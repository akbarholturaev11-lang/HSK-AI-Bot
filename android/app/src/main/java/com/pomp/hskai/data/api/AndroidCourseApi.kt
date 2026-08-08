package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface AndroidCourseApi {

    /**
     * @param timezoneOffsetMinutes device offset, sent so the server can keep
     * streak day boundaries correct. UTC+0 is a real value and is always sent.
     */
    @GET("api/v3/android/course/map")
    suspend fun courseMap(
        @Header("Authorization") authorization: String,
        @Query("tz") timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto>

    @GET("api/v3/android/course/lesson/{lessonOrder}")
    suspend fun lesson(
        @Header("Authorization") authorization: String,
        @Path("lessonOrder") lessonOrder: Int,
    ): Response<kotlinx.serialization.json.JsonObject>

    @POST("api/v3/android/course/complete")
    suspend fun complete(
        @Header("Authorization") authorization: String,
        @Body body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse>

    @POST("api/v3/android/preferences/language")
    suspend fun setLanguage(
        @Header("Authorization") authorization: String,
        @Body body: LanguageRequest,
    ): Response<OkResponse>
}
