package com.example.healthconnect_export

import android.os.Bundle

import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.records.NutritionRecord
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.StepsRecord

import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager

import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        HealthConnectClient.getOrCreate(this)

        val weightSyncRequest =
            PeriodicWorkRequestBuilder<WeightSyncWorker>(
                6,
                TimeUnit.HOURS
            ).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "weight_sync",
            ExistingPeriodicWorkPolicy.UPDATE,
            weightSyncRequest
        )

        val nutritionSyncRequest =
            PeriodicWorkRequestBuilder<NutritionSyncWorker>(
                6,
                TimeUnit.HOURS
            ).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "nutrition_sync",
            ExistingPeriodicWorkPolicy.UPDATE,
            nutritionSyncRequest
        )

        val activitySyncRequest =
            PeriodicWorkRequestBuilder<ActivitySyncWorker>(
                6,
                TimeUnit.HOURS
            ).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "activity_sync",
            ExistingPeriodicWorkPolicy.UPDATE,
            activitySyncRequest
        )

        setContent {
            var text by remember {
                mutableStateOf("Bereit")
            }

            val permissions = setOf(
                HealthPermission.getReadPermission(WeightRecord::class),
                HealthPermission.getReadPermission(NutritionRecord::class),
                HealthPermission.getReadPermission(ActiveCaloriesBurnedRecord::class),
                HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
                HealthPermission.getReadPermission(StepsRecord::class)
            )

            val permissionLauncher =
                rememberLauncherForActivityResult(
                    PermissionController
                        .createRequestPermissionResultContract()
                ) { granted: Set<String> ->

                    text =
                        if (granted.containsAll(permissions)) {
                            "Health Connect Berechtigungen erteilt."
                        } else {
                            "Nicht alle Berechtigungen erteilt."
                        }
                }

            Surface(
                modifier = Modifier.fillMaxSize()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(text)

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            permissionLauncher.launch(permissions)
                        }
                    ) {
                        Text("Health Connect erlauben")
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<WeightSyncWorker>()
                                        .build()
                                )

                            text = "Gewichtssync gestartet."
                        }
                    ) {
                        Text("Gewicht synchronisieren")
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<NutritionSyncWorker>()
                                        .build()
                                )

                            text = "Nutrition-Sync gestartet."
                        }
                    ) {
                        Text("Nutrition synchronisieren")
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<ActivitySyncWorker>()
                                        .build()
                                )

                            text = "Activity-Sync gestartet."
                        }
                    ) {
                        Text("Aktivität synchronisieren")
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = {
                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<WeightSyncWorker>()
                                        .build()
                                )

                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<NutritionSyncWorker>()
                                        .build()
                                )

                            WorkManager.getInstance(this@MainActivity)
                                .enqueue(
                                    OneTimeWorkRequestBuilder<ActivitySyncWorker>()
                                        .build()
                                )

                            text = "Alle Syncs gestartet."
                        }
                    ) {
                        Text("Alles synchronisieren")
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Text(
                        "Gewicht, Nutrition und Aktivität laufen zusätzlich automatisch alle 6 Stunden im Hintergrund.",
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
            }
        }
    }
}