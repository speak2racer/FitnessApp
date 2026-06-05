package com.example.healthconnect_export

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.NutritionRecord
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
data class NutritionDailyLog(
    val log_date: String,
    val calories: Double,
    val protein: Double,
    val carbs: Double,
    val fat: Double,
    val source: String = "health_connect"
)

class NutritionSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val client = HealthConnectClient.getOrCreate(applicationContext)
            val zoneId = ZoneId.systemDefault()

            val startDate = LocalDate.now().minusDays(30)
            val endDate = LocalDate.now()
            val start = startDate.atStartOfDay(zoneId).toInstant()
            val end = endDate.plusDays(1).atStartOfDay(zoneId).toInstant()

            val records = client.readRecords(
                ReadRecordsRequest(
                    recordType = NutritionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            ).records

            val dailyLogs = records
                .groupBy { it.startTime.atZone(zoneId).toLocalDate() }
                .map { (day, recs) ->
                    var calories = 0.0; var protein = 0.0
                    var carbs = 0.0; var fat = 0.0
                    recs.forEach { r ->
                        calories += r.energy?.inKilocalories ?: 0.0
                        protein += r.protein?.inGrams ?: 0.0
                        carbs += r.totalCarbohydrate?.inGrams ?: 0.0
                        fat += r.totalFat?.inGrams ?: 0.0
                    }
                    NutritionDailyLog(
                        log_date = day.format(DateTimeFormatter.ISO_LOCAL_DATE),
                        calories = calories, protein = protein,
                        carbs = carbs, fat = fat
                    )
                }
                .filter { it.calories > 0 }
                .sortedBy { it.log_date }

            if (dailyLogs.isNotEmpty()) {
                SupabaseConfig.client
                    .from("nutrition_daily_logs")
                    .upsert(dailyLogs) { onConflict = "log_date" }
            }

            val timestamp = java.time.LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm"))
            SyncPreferences.setLastSync(applicationContext, "nutrition", timestamp)
            SyncPreferences.setLastError(applicationContext, "nutrition", "")

            Result.success()

        } catch (e: Exception) {
            SyncPreferences.setLastError(applicationContext, "nutrition", e.message ?: "Unbekannter Fehler")
            Result.failure()
        }
    }
}
