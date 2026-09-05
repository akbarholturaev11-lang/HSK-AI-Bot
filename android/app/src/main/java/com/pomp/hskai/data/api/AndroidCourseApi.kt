package com.pomp.hskai.data.api

import okhttp3.ResponseBody
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
    ): Response<CourseLessonResponse>

    @GET("api/v3/android/tts")
    suspend fun tts(
        @Header("Authorization") authorization: String,
        @Query("text") text: String,
        @Query("rate") rate: String = "-10%",
    ): Response<ResponseBody>

    @POST("api/v3/android/course/complete")
    suspend fun complete(
        @Header("Authorization") authorization: String,
        @Body body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse>

    @POST("api/v3/android/course/reward-chest/open")
    suspend fun openRewardChest(
        @Header("Authorization") authorization: String,
    ): Response<RewardChestOpenResponse>

    @GET("api/v3/android/dictionary")
    suspend fun dictionary(
        @Header("Authorization") authorization: String,
        @Header("If-None-Match") ifNoneMatch: String? = null,
    ): Response<DictionaryResponse>

    @POST("api/v3/android/preferences/language")
    suspend fun setLanguage(
        @Header("Authorization") authorization: String,
        @Body body: LanguageRequest,
    ): Response<OkResponse>

    @POST("api/v3/android/preferences/notifications")
    suspend fun setNotifications(
        @Header("Authorization") authorization: String,
        @Body body: NotificationsRequest,
    ): Response<OkResponse>
}
