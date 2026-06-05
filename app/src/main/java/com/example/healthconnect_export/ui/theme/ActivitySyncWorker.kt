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

import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.postgrest.Postgrest
import io.github.jan.supabase.postgrest.from

import kotlinx.serialization.Serializable
import java.time.LocalDate
import java.time.ZoneId

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

    private val healthConnectClient =
        HealthConnectClient.getOrCreate(context)

    private val supabase = createSupabaseClient(
        supabaseUrl = "https://zhttlbhpyxcqnujirbxk.supabase.co",
        supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodHRsYmhweXhjcW51amlyYnhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2ODgxODcsImV4cCI6MjA5NTI2NDE4N30.IHSHYwdUJ4ZlqX9q9Qssuw3QUtotLM_yLFz6gzj89UI"
    ) {
        install(Postgrest)
    }

    override suspend fun doWork(): Result {
        return try {
            val zoneId = ZoneId.systemDefault()
            val startDate = LocalDate.now().minusDays(30)
            val endDate = LocalDate.now()

            val dailyLogs = mutableListOf<ActivityDailyLog>()

            var day = startDate

            while (!day.isAfter(endDate)) {
                val start = day.atStartOfDay(zoneId).toInstant()
                val end = day.plusDays(1).atStartOfDay(zoneId).toInstant()

                val timeRange = TimeRangeFilter.between(start, end)

                val activeCalories =
                    healthConnectClient.readRecords(
                        ReadRecordsRequest(
                            recordType = ActiveCaloriesBurnedRecord::class,
                            timeRangeFilter = timeRange
                        )
                    ).records.sumOf {
                        it.energy.inKilocalories
                    }

                val totalCalories =
                    healthConnectClient.readRecords(
                        ReadRecordsRequest(
                            recordType = TotalCaloriesBurnedRecord::class,
                            timeRangeFilter = timeRange
                        )
                    ).records.sumOf {
                        it.energy.inKilocalories
                    }

                val steps =
                    healthConnectClient.readRecords(
                        ReadRecordsRequest(
                            recordType = StepsRecord::class,
                            timeRangeFilter = timeRange
                        )
                    ).records.sumOf {
                        it.count
                    }

                dailyLogs.add(
                    ActivityDailyLog(
                        log_date = day.toString(),
                        active_calories = activeCalories,
                        total_calories = totalCalories,
                        steps = steps
                    )
                )

                day = day.plusDays(1)
            }

            dailyLogs.forEach { log ->
                supabase
                    .from("activity_daily_logs")
                    .upsert(
                        log,
                        onConflict = "log_date"
                    )
            }

            println("Activity erfolgreich synchronisiert: $dailyLogs")

            Result.success()

        } catch (e: Exception) {
            e.printStackTrace()
            println("ActivitySyncWorker Fehler: ${e.message}")
            Result.failure()
        }
    }
}