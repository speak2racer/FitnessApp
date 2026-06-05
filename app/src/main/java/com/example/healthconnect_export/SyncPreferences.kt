package com.example.healthconnect_export

import android.content.Context

object SyncPreferences {
    private const val PREFS = "sync_prefs"

    fun setLastSync(context: Context, key: String, timestamp: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(key, timestamp).apply()
    }

    fun setLastError(context: Context, key: String, error: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("${key}_error", error).apply()
    }

    fun getLastSync(context: Context, key: String): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(key, "Noch nie") ?: "Noch nie"

    fun getLastError(context: Context, key: String): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("${key}_error", "") ?: ""
}
