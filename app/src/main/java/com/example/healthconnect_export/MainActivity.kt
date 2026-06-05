package com.example.healthconnect_export

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.work.*
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        enqueueSyncs()

        setContent {
            var statusText by remember { mutableStateOf("") }
            var berechtigungenErteilt by remember { mutableStateOf(false) }

            val permissions = setOf(
                HealthPermission.getReadPermission(WeightRecord::class),
                HealthPermission.getReadPermission(NutritionRecord::class),
                HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
                HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
                HealthPermission.getReadPermission(StepsRecord::class)
            )

            val permissionLauncher = rememberLauncherForActivityResult(
                PermissionController.createRequestPermissionResultContract()
            ) { granted ->
                berechtigungenErteilt = granted.containsAll(permissions)
                statusText = if (berechtigungenErteilt)
                    "✅ Health Connect Berechtigungen erteilt."
                else
                    "⚠️ Nicht alle Berechtigungen erteilt."
            }

            val weightSync = SyncPreferences.getLastSync(this, "weight")
            val nutritionSync = SyncPreferences.getLastSync(this, "nutrition")
            val activitySync = SyncPreferences.getLastSync(this, "activity")
            val weightError = SyncPreferences.getLastError(this, "weight")
            val nutritionError = SyncPreferences.getLastError(this, "nutrition")
            val activityError = SyncPreferences.getLastError(this, "activity")

            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp)
                            .verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "🏋️ Health Connect Sync",
                            style = MaterialTheme.typography.headlineMedium
                        )

                        // Berechtigungen
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("Berechtigungen",
                                    style = MaterialTheme.typography.titleMedium)
                                Button(
                                    onClick = { permissionLauncher.launch(permissions) },
                                    modifier = Modifier.fillMaxWidth()
                                ) { Text("Health Connect erlauben") }
                                if (statusText.isNotEmpty()) {
                                    Text(statusText, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }

                        // Sync-Status
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("Letzter Sync",
                                    style = MaterialTheme.typography.titleMedium)
                                SyncStatusRow("⚖️ Gewicht", weightSync, weightError)
                                SyncStatusRow("🍽️ Ernährung", nutritionSync, nutritionError)
                                SyncStatusRow("🏃 Aktivität", activitySync, activityError)
                            }
                        }

                        // Manueller Sync
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("Manuell synchronisieren",
                                    style = MaterialTheme.typography.titleMedium)

                                Button(
                                    onClick = {
                                        enqueueOnce<WeightSyncWorker>("weight_once")
                                        statusText = "⚖️ Gewichtssync gestartet..."
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) { Text("Gewicht synchronisieren") }

                                Button(
                                    onClick = {
                                        enqueueOnce<NutritionSyncWorker>("nutrition_once")
                                        statusText = "🍽️ Ernährungssync gestartet..."
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) { Text("Ernährung synchronisieren") }

                                Button(
                                    onClick = {
                                        enqueueOnce<ActivitySyncWorker>("activity_once")
                                        statusText = "🏃 Aktivitätssync gestartet..."
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) { Text("Aktivität synchronisieren") }

                                Button(
                                    onClick = {
                                        enqueueOnce<WeightSyncWorker>("weight_once")
                                        enqueueOnce<NutritionSyncWorker>("nutrition_once")
                                        enqueueOnce<ActivitySyncWorker>("activity_once")
                                        statusText = "🔄 Alle Syncs gestartet..."
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = MaterialTheme.colorScheme.primary
                                    )
                                ) { Text("🔄 Alles synchronisieren") }

                                if (statusText.isNotEmpty()) {
                                    Text(statusText, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }

                        Text(
                            "Automatischer Sync läuft alle 6 Stunden im Hintergrund.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }

    private fun enqueueSyncs() {
        fun enqueue(name: String, clazz: Class<out CoroutineWorker>) {
            val request = PeriodicWorkRequestBuilder(clazz, 6, TimeUnit.HOURS).build()
            WorkManager.getInstance(this).enqueueUniquePeriodicWork(
                name, ExistingPeriodicWorkPolicy.UPDATE, request
            )
        }
        enqueue("weight_sync", WeightSyncWorker::class.java)
        enqueue("nutrition_sync", NutritionSyncWorker::class.java)
        enqueue("activity_sync", ActivitySyncWorker::class.java)
    }

    private inline fun <reified T : CoroutineWorker> enqueueOnce(tag: String) {
        WorkManager.getInstance(this).enqueue(
            OneTimeWorkRequestBuilder<T>().addTag(tag).build()
        )
    }
}

@Composable
fun SyncStatusRow(label: String, lastSync: String, error: String) {
    Row(modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
            Text(lastSync, style = MaterialTheme.typography.bodySmall)
            if (error.isNotEmpty()) {
                Text("❌ $error",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Red)
            }
        }
    }
}
