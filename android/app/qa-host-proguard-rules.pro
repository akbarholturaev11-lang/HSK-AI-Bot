# A separately minified test APK must retain the shared runtime ABI loaded by
# AndroidJUnitRunner. Keep these support symbols; allow their bodies to optimize.
# Only the explicit signed qaRelease build type reads this file.
-keep,allowoptimization class androidx.tracing.** { *; }
-keep,allowoptimization class kotlin.** { *; }
-keep,allowoptimization class kotlinx.coroutines.** { *; }

# Explicit instrumentation entry points that production R8 may inline away.
# Preserve API signatures, while retaining optimization of their implementations
# and the underlying auth, bridge, journal, HTTP and OS delivery paths.
-keepclassmembers,allowoptimization class com.pomp.hskai.HskAiApplication {
    public *** getCredentialStore();
    public *** getStudyReminderCoordinator();
}
-keepclassmembers,allowoptimization class com.pomp.hskai.core.storage.SecureCredentialStore {
    public java.lang.Object refreshToken(...);
    public java.lang.Object saveRefreshToken(...);
}
-keepclassmembers,allowoptimization class com.pomp.hskai.core.auth.AuthRepository {
    public java.lang.Object bootstrap(...);
    public java.lang.Object logout(...);
}
-keep,allowoptimization class com.pomp.hskai.core.notify.StudyNotifications { public *; }
-keep,allowoptimization class com.pomp.hskai.core.notify.StudyReminderCoordinator { public *; }
-keep,allowoptimization class com.pomp.hskai.core.notify.StudyReminderCoordinator$Outcome { *; }
