package com.example.healthconnect_export

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import io.github.jan.supabase.postgrest.from
import io.github.jan.supabase.postgrest.query.Order
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.round

@Serializable
data class NutritionTarget(
    val datum: String,
    val kalorien: Int,
    val eiweiss: Int,
    val fett: Int,
    val kohlenhydrate: Int,
    val faktor: Double,
    val carb_anteil: Int
)

class NutritionTargetSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            // 1. Faktor + Carb-Anteil aus Supabase lesen
            val (faktor, carbAnteilBase) = fetchFaktorFromSupabase()
                ?: return Result.failure()

            // 2. KFA aus Supabase Caliper lesen
            val kfa = fetchKfaFromSupabase() ?: 15.0

            // 3. Gewicht aus Health Connect
            val gewichtKg = fetchTodayWeight() ?: fetchLatestWeight()
                ?: return Result.failure()

            // 4. Makros berechnen (gleiche Formel wie Python)
            val target = berechneMakros(gewichtKg, faktor, kfa)

            // 5. Heutigen nutrition_target in Supabase schreiben
            SupabaseConfig.client
                .from("nutrition_targets")
                .upsert(target) { onConflict = "datum" }

            val timestamp = java.time.LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm"))
            SyncPreferences.setLastSync(applicationContext, "nutrition_target", timestamp)
            SyncPreferences.setLastError(applicationContext, "nutrition_target", "")

            Result.success()

        } catch (e: Exception) {
            SyncPreferences.setLastError(applicationContext, "nutrition_target", e.message ?: "Fehler")
            Result.failure()
        }
    }

    private fun berechneMakros(gewichtKg: Double, faktor: Double, kfa: Double): NutritionTarget {
        val gewichtLbs = gewichtKg * 2.20462
        val kalorien = round(gewichtLbs * faktor).toInt()
        val eiweissG = round(gewichtLbs).toInt()
        val eiweissKcal = eiweissG * 4
        val restKalorien = kalorien - eiweissKcal

        val carbAnteil = when {
            kfa >= 15 -> 40
            kfa >= 12 -> 50
            else -> 60
        }

        val kohlenhydrateKcal = restKalorien * (carbAnteil / 100.0)
        val kohlenhydrateG = round(kohlenhydrateKcal / 4).toInt()
        val fettKcal = restKalorien - kohlenhydrateKcal
        val fettG = round(fettKcal / 9).toInt()

        return NutritionTarget(
            datum = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE),
            kalorien = kalorien,
            eiweiss = eiweissG,
            fett = fettG,
            kohlenhydrate = kohlenhydrateG,
            faktor = faktor,
            carb_anteil = carbAnteil
        )
    }

    private suspend fun fetchFaktorFromSupabase(): Pair<Double, Int>? =
        withContext(Dispatchers.IO) {
            try {
                val url = URL("${SupabaseConfig.url}/rest/v1/nutrition_targets?select=faktor,carb_anteil&order=datum.desc&limit=1")
                val conn = url.openConnection() as HttpURLConnection
                conn.setRequestProperty("apikey", SupabaseConfig.key)
                conn.setRequestProperty("Authorization", "Bearer ${SupabaseConfig.key}")
                val text = conn.inputStream.bufferedReader().readText()
                val arr = Json.parseToJsonElement(text).jsonArray
                if (arr.isEmpty()) return@withContext null
                val obj = arr[0].jsonObject
                val faktor = obj["faktor"]?.jsonPrimitive?.doubleOrNull ?: return@withContext null
                val carb = obj["carb_anteil"]?.jsonPrimitive?.doubleOrNull?.toInt() ?: 40
                Pair(faktor, carb)
            } catch (e: Exception) { null }
        }

    private suspend fun fetchKfaFromSupabase(): Double? =
        withContext(Dispatchers.IO) {
            try {
                val url = URL("${SupabaseConfig.url}/rest/v1/caliper?select=kfa&order=datum.desc&limit=1")
                val conn = url.openConnection() as HttpURLConnection
                conn.setRequestProperty("apikey", SupabaseConfig.key)
                conn.setRequestProperty("Authorization", "Bearer ${SupabaseConfig.key}")
                val text = conn.inputStream.bufferedReader().readText()
                val arr = Json.parseToJsonElement(text).jsonArray
                if (arr.isEmpty()) return@withContext null
                arr[0].jsonObject["kfa"]?.jsonPrimitive?.doubleOrNull
            } catch (e: Exception) { null }
        }

    private suspend fun fetchTodayWeight(): Double? {
        val client = HealthConnectClient.getOrCreate(applicationContext)
        val zoneId = ZoneId.systemDefault()
        val today = LocalDate.now()
        val start = today.atStartOfDay(zoneId).toInstant()
        val end = Instant.now()
        val records = client.readRecords(
            ReadRecordsRequest(WeightRecord::class, TimeRangeFilter.between(start, end))
        ).records
        return records.maxByOrNull { it.time }?.weight?.inKilograms
    }

    private suspend fun fetchLatestWeight(): Double? {
        val client = HealthConnectClient.getOrCreate(applicationContext)
        val zoneId = ZoneId.systemDefault()
        val start = LocalDate.now().minusDays(7).atStartOfDay(zoneId).toInstant()
        val records = client.readRecords(
            ReadRecordsRequest(WeightRecord::class, TimeRangeFilter.between(start, Instant.now()))
        ).records
        return records.maxByOrNull { it.time }?.weight?.inKilograms
    }
}
