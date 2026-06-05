package com.example.healthconnect_export

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import io.github.jan.supabase.postgrest.from
import kotlinx.serialization.Serializable
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Serializable
data class WeightEntry(
    val datum: String,
    val gewicht: Double
)

class WeightSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val client = HealthConnectClient.getOrCreate(applicationContext)
            val zoneId = ZoneId.systemDefault()

            val start = LocalDate.now().minusDays(14).atStartOfDay(zoneId).toInstant()
            val end = Instant.now()

            val records = client.readRecords(
                ReadRecordsRequest(
                    recordType = WeightRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            ).records
                .groupBy { it.time.atZone(zoneId).toLocalDate() }
                .map { (_, dayRecords) -> dayRecords.maxBy { it.time } }
                .sortedBy { it.time }

            if (records.isEmpty()) {
                SyncPreferences.setLastSync(applicationContext, "weight", "Keine Daten")
                return Result.success()
            }

            val entries = records.map { record ->
                WeightEntry(
                    datum = record.time.atZone(zoneId).toLocalDate()
                        .format(DateTimeFormatter.ISO_LOCAL_DATE),
                    gewicht = record.weight.inKilograms
                )
            }

            SupabaseConfig.client
                .from("weights")
                .upsert(entries) { onConflict = "datum" }

            val timestamp = java.time.LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm"))
            SyncPreferences.setLastSync(applicationContext, "weight", timestamp)
            SyncPreferences.setLastError(applicationContext, "weight", "")

            Result.success()

        } catch (e: Exception) {
            SyncPreferences.setLastError(applicationContext, "weight", e.message ?: "Unbekannter Fehler")
            Result.failure()
        }
    }
}
