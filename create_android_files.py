import os
import shutil

# 创建目录
dirs = [
    'android/app/src/main/res/values',
    'android/app/src/main/assets/www',
    'android/gradle/wrapper',
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f'Created directory: {d}')

# 创建 build.gradle (Module)
with open('android/app/build.gradle', 'w', encoding='utf-8') as f:
    f.write("""plugins {
    id 'com.android.application'
}

android {
    namespace 'com.example.stressassessment'
    compileSdk 34

    defaultConfig {
        applicationId 'com.example.stressassessment'
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName '1.0'
        testInstrumentationRunner 'androidx.test.runner.AndroidJUnitRunner'
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
""")
print('Created: android/app/build.gradle')

# 创建 build.gradle (Project)
with open('android/build.gradle', 'w', encoding='utf-8') as f:
    f.write("""plugins {
    id 'com.android.application' version '8.1.2' apply false
    id 'com.android.library' version '8.1.2' apply false
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
""")
print('Created: android/build.gradle')

# 创建 settings.gradle
with open('android/settings.gradle', 'w', encoding='utf-8') as f:
    f.write("""pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = 'StressAssessment'
include ':app'
""")
print('Created: android/settings.gradle')

# 创建 gradle-wrapper.properties
with open('android/gradle/wrapper/gradle-wrapper.properties', 'w', encoding='utf-8') as f:
    f.write("""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.4-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
""")
print('Created: android/gradle/wrapper/gradle-wrapper.properties')

# 创建 proguard-rules.pro
with open('android/app/proguard-rules.pro', 'w', encoding='utf-8') as f:
    f.write("# Add project specific ProGuard rules here.\n")
print('Created: android/app/proguard-rules.pro')

# 创建 strings.xml
with open('android/app/src/main/res/values/strings.xml', 'w', encoding='utf-8') as f:
    f.write('<resources>\n    <string name="app_name">压力评估</string>\n</resources>\n')
print('Created: android/app/src/main/res/values/strings.xml')

# 创建 styles.xml
with open('android/app/src/main/res/values/styles.xml', 'w', encoding='utf-8') as f:
    f.write("""<resources>
    <style name="Theme.StressAssessment" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">#6200EE</item>
        <item name="colorPrimaryDark">#3700B3</item>
        <item name="colorAccent">#03DAC6</item>
    </style>
</resources>
""")
print('Created: android/app/src/main/res/values/styles.xml')

# 创建 colors.xml
with open('android/app/src/main/res/values/colors.xml', 'w', encoding='utf-8') as f:
    f.write('<resources>\n    <color name="primary">#6200EE</color>\n    <color name="primaryDark">#3700B3</color>\n    <color name="accent">#03DAC6</color>\n</resources>\n')
print('Created: android/app/src/main/res/values/colors.xml')

# 复制前端文件
frontend_dir = 'stress/stress  test'
assets_dir = 'android/app/src/main/assets/www'
if os.path.exists(frontend_dir):
    for item in os.listdir(frontend_dir):
        src = os.path.join(frontend_dir, item)
        dst = os.path.join(assets_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    print('Copied frontend files to assets/www')
else:
    print('Frontend directory not found')

# 复制图片文件
image_dir = 'backend/image'
if os.path.exists(image_dir):
    os.makedirs(os.path.join(assets_dir, 'images'), exist_ok=True)
    for item in os.listdir(image_dir):
        src = os.path.join(image_dir, item)
        dst = os.path.join(assets_dir, 'images', item)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    print('Copied images to assets/www/images')
else:
    print('Image directory not found')

print('\n=== All files created successfully! ===')
