# Selected by the explicit driver through its class name and JUnit reflection.
-keep,allowoptimization class com.pomp.hskai.core.notify.SmartStudySignedStagingTest { *; }
-keep class androidx.test.ext.junit.runners.AndroidJUnit4 { public <init>(java.lang.Class); }
-keepattributes *Annotation*
