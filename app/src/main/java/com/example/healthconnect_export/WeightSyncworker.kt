package com.example.healthconnect_export

import android.content.Context

import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter

import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

import java.net.HttpURLConnection
import java.net.URL

import java.time.Instant
import java.time.ZoneId

class WeightSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private val supabaseUrl =
        "https://zhttlbhpyxcqnujirbxk.supabase.co"

    private val supabaseAnonKey =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodHRsYmhweXhjcW51amlyYnhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2ODgxODcsImV4cCI6MjA5NTI2NDE4N30.IHSHYwdUJ4ZlqX9q9Qssuw3QUtotLM_yLFz6gzj89UI"

    override suspend fun doWork(): Result {
        return try {
            val client =
                HealthConnectClient.getOrCreate(applicationContext)

            val response =
                client.readRecords(
                    ReadRecordsRequest(
                        recordType = WeightRecord::class,
                        timeRangeFilter =
                            TimeRangeFilter.between(
                                Instant.parse("2020-01-01T00:00:00Z"),
                                Instant.now()
                            )
                    )
                )

            val records =
                response.records
                    .groupBy {
                        it.time
                            .atZone(ZoneId.systemDefault())
                            .toLocalDate()
                    }
                    .map { (_, dayRecords) ->
                        dayRecords.maxBy { it.time }
                    }
                    .sortedBy { it.time }

            println("Gefundene Gewichtseinträge: ${records.size}")

            if (records.isEmpty()) {
                println("Keine Gewichtsdaten gefunden.")
                return Result.success()
            }

            val json =
                records.joinToString(
                    prefix = "[",
                    postfix = "]"
                ) { record ->

                    val datum =
                        record.time
                            .atZone(ZoneId.systemDefault())
                            .toLocalDate()
                            .toString()

                    val gewicht =
                        record.weight.inKilograms

                    println("Gewicht gefunden: $gewicht kg am $datum")

                    """
                    {
                        "datum": "$datum",
                        "gewicht": $gewicht
                    }
                    """.trimIndent()
                }

            println("JSON für Supabase:")
            println(json)

            uploadToSupabase(json)

            println("Gewicht erfolgreich nach Supabase hochgeladen.")

            Result.success()

        } catch (e: Exception) {
            e.printStackTrace()
            println("WeightSyncWorker Fehler: ${e.message}")
            Result.failure()
        }
    }

    private suspend fun uploadToSupabase(
        json: String
    ) {
        withContext(Dispatchers.IO) {
            val url = URL(
                "${supabaseUrl}/rest/v1/weights?on_conflict=datum"
            )

            val connection =
                url.openConnection() as HttpURLConnection

            connection.requestMethod = "POST"
            connection.doOutput = true

            connection.setRequestProperty(
                "Content-Type",
                "application/json"
            )

            connection.setRequestProperty(
                "apikey",
                supabaseAnonKey
            )

            connection.setRequestProperty(
                "Authorization",
                "Bearer $supabaseAnonKey"
            )

            connection.setRequestProperty(
                "Prefer",
                "resolution=merge-duplicates,return=representation"
            )

            connection.outputStream.use { stream ->
                stream.write(json.toByteArray())
            }

            val code =
                connection.responseCode

            println("Supabase HTTP Code: $code")

            val responseText =
                if (code in 200..299) {
                    connection.inputStream
                        ?.bufferedReader()
                        ?.readText()
                } else {
                    connection.errorStream
                        ?.bufferedReader()
                        ?.readText()
                }

            println("Supabase Antwort: $responseText")

            if (code !in 200..299) {
                throw Exception(
                    "Supabase Fehler $code: $responseText"
                )
            }

            connection.disconnect()
        }
    }
}