package com.example.healthconnect_export

import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.postgrest.Postgrest

object SupabaseConfig {
    val url: String get() = BuildConfig.SUPABASE_URL
    val key: String get() = BuildConfig.SUPABASE_ANON_KEY

    val client by lazy {
        createSupabaseClient(supabaseUrl = url, supabaseKey = key) {
            install(Postgrest)
        }
    }
}
