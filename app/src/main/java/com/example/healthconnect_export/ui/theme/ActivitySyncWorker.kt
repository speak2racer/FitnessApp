package com.example.healthconnect_export

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import io.github.jan.supabase.postgrest.from
import kotlinx.serialization.Serializable
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Serializable
data class ActivityDailyLog(
    val log_date: String,
    val active_calories: Double,
    val total_calories: Double,
    val steps: Long,
    val source: String = "health_connect"
)

class ActivitySyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val client = HealthConnectClient.getOrCreate(applicationContext)
            val zoneId = ZoneId.systemDefault()

            val startDate = LocalDate.now().minusDays(30)
            val endDate = LocalDate.now()
            val logs = mutableListOf<ActivityDailyLog>()

            var day = startDate
            while (!day.isAfter(endDate)) {
                val start = day.atStartOfDay(zoneId).toInstant()
                val end = day.plusDays(1).atStartOfDay(zoneId).toInstant()
                val range = TimeRangeFilter.between(start, end)

                val activeCalories = client.readRecords(
                    ReadRecordsRequest(ActiveCaloriesBurnedRecord::class, range)
                ).records.sumOf { it.energy.inKilocalories }

                val totalCalories = client.readRecords(
                    ReadRecordsRequest(TotalCaloriesBurnedRecord::class, range)
                ).records.sumOf { it.energy.inKilocalories }

                val steps = client.readRecords(
                    ReadRecordsRequest(StepsRecord::class, range)
                ).records.sumOf { it.count }

                // Nur Tage mit echten Daten speichern
                if (totalCalories > 0 || steps > 0) {
                    logs.add(ActivityDailyLog(
                        log_date = day.format(DateTimeFormatter.ISO_LOCAL_DATE),
                        active_calories = activeCalories,
                        total_calories = totalCalories,
                        steps = steps
                    ))
                }

                day = day.plusDays(1)
            }

            if (logs.isNotEmpty()) {
                SupabaseConfig.client
                    .from("activity_daily_logs")
                    .upsert(logs) { onConflict = "log_date" }
            }

            val timestamp = java.time.LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm"))
            SyncPreferences.setLastSync(applicationContext, "activity", timestamp)
            SyncPreferences.setLastError(applicationContext, "activity", "")

            Result.success()

        } catch (e: Exception) {
            SyncPreferences.setLastError(applicationContext, "activity", e.message ?: "Unbekannter Fehler")
            Result.failure()
        }
    }
}
