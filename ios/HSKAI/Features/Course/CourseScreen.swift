import SwiftUI

struct CourseScreen: View {
    @ObservedObject var model: CourseViewModel
    let account: LinkedAccount

    @State private var foundationModel: FoundationViewModel?
    @State private var showingFoundation = false
    @State private var lessonModel: LessonViewModel?
    @State private var showingLesson = false

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()

                if model.isLoading && model.map == nil {
                    ProgressView().tint(HSKColors.cinnabar).controlSize(.large)
                } else if let map = model.map {
                    ScrollView(showsIndicators: false) {
                        VStack(spacing: 14) {
                            CourseSummaryCard(map: map)

                            if model.isStale {
                                Text("course_offline_cache")
                                    .font(.footnote)
                                    .foregroundStyle(HSKColors.inkSecondary)
                                    .frame(maxWidth: .infinity)
                                    .padding(10)
                                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                                            .stroke(Color.white.opacity(0.42), lineWidth: 0.8)
                                    )
                            }

                            if let foundation = map.foundation,
                               foundation.required,
                               !foundation.completed {
                                FoundationGateCard {
                                    foundationModel = FoundationViewModel(
                                        api: model.api,
                                        language: map.user.language
                                    )
                                    showingFoundation = true
                                }
                            }

                            if let today = map.today, !today.tasks.isEmpty {
                                TodayPlanSummary(today: today)
                            }

                            ForEach(map.units) { unit in
                                CourseUnitCard(
                                    unit: unit,
                                    language: map.user.language
                                ) { lesson in
                                    lessonModel = LessonViewModel(
                                        api: model.api,
                                        lessonOrder: lesson.order,
                                        language: map.user.language
                                    )
                                    showingLesson = true
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                    }
                    .refreshable {
                        await model.load(scope: account.deviceId, force: true)
                    }
                } else {
                    VStack(spacing: 16) {
                        Text(LocalizedStringKey(model.errorKey ?? "error_network"))
                            .foregroundStyle(HSKColors.inkSecondary)
                            .multilineTextAlignment(.center)
                        Button("action_retry") {
                            Task { await model.load(scope: account.deviceId, force: true) }
                        }
                        .buttonStyle(HSKPrimaryButtonStyle())
                    }
                    .padding(24)
                }
            }
            .navigationTitle("tab_course")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task(id: account.deviceId) {
            await model.load(scope: account.deviceId)
        }
        .fullScreenCover(isPresented: $showingLesson) {
            if let lessonModel {
                LessonScreen(
                    model: lessonModel,
                    onClose: {
                        showingLesson = false
                    },
                    onCompleted: {
                        Task {
                            await model.load(scope: account.deviceId, force: true)
                        }
                    }
                )
            }
        }
        .fullScreenCover(isPresented: $showingFoundation) {
            if let foundationModel {
                FoundationScreen(
                    model: foundationModel,
                    required: model.map?.foundation?.required == true,
                    onCompleted: {
                        showingFoundation = false
                        Task {
                            await model.load(scope: account.deviceId, force: true)
                        }
                    },
                    onClose: {
                        showingFoundation = false
                    }
                )
            }
        }
    }
}

private struct FoundationGateCard: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HSKGlassCard(cornerRadius: 24, padding: 17, tint: HSKColors.cinnabar) {
                HStack(spacing: 14) {
                    ZStack {
                        Circle()
                            .fill(HSKColors.cinnabar.opacity(0.14))
                            .frame(width: 52, height: 52)
                        Image(systemName: "sparkles")
                            .font(.title3.weight(.bold))
                            .foregroundStyle(HSKColors.cinnabar)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("foundation_gate_title")
                            .font(.headline)
                            .foregroundStyle(HSKColors.ink)
                        Text("foundation_gate_subtitle")
                            .font(.caption)
                            .foregroundStyle(HSKColors.inkSecondary)
                            .multilineTextAlignment(.leading)
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(HSKColors.inkSecondary)
                }
            }
        }
        .buttonStyle(.plain)
    }
}

private struct CourseSummaryCard: View {
    let map: IOSCourseMap

    var body: some View {
        HStack(spacing: 12) {
            metric(icon: "bolt.fill", value: String(map.progress.xp), label: "course_xp")
            Divider().frame(height: 38)
            metric(icon: "flame.fill", value: String(map.progress.streak), label: "course_streak")
            Divider().frame(height: 38)
            metric(icon: "trophy.fill", value: map.progress.league.isEmpty ? "—" : map.progress.league, label: "course_league")
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .stroke(Color.white.opacity(0.52), lineWidth: 0.9)
        )
        .shadow(color: Color.black.opacity(0.08), radius: 16, y: 8)
    }

    private func metric(icon: String, value: String, label: LocalizedStringKey) -> some View {
        VStack(spacing: 4) {
            Image(systemName: icon).foregroundStyle(HSKColors.cinnabar)
            Text(value).font(.headline).foregroundStyle(HSKColors.ink).lineLimit(1).minimumScaleFactor(0.72)
            Text(label).font(.caption2).foregroundStyle(HSKColors.inkSecondary)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct TodayPlanSummary: View {
    let today: IOSCourseToday

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("today_plan", systemImage: "target").font(.headline).foregroundStyle(.white)
                Spacer()
                Text("\(today.doneXp)/\(today.goalXp) XP")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.78))
            }

            ProgressView(value: Double(min(today.doneXp, today.goalXp)), total: Double(max(1, today.goalXp)))
                .tint(HSKColors.jade)

            HStack(spacing: 8) {
                ForEach(Array(today.tasks.prefix(4))) { task in
                    VStack(spacing: 5) {
                        Image(systemName: taskIcon(task))
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(task.done ? HSKColors.jade : .white)
                            .frame(width: 32, height: 32)
                            .background(Circle().fill(Color.white.opacity(0.10)))
                        Text(taskLabel(task))
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.74))
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding(16)
        .background {
            ZStack {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(.ultraThinMaterial)
                LinearGradient(
                    colors: [
                        HSKColors.ink.opacity(0.88),
                        HSKColors.ink.opacity(0.70),
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .stroke(Color.white.opacity(0.20), lineWidth: 0.8)
        )
        .shadow(color: Color.black.opacity(0.16), radius: 18, y: 9)
    }

    private func taskIcon(_ task: IOSCourseTodayTask) -> String {
        if task.done { return "checkmark" }
        if !task.available { return "lock.fill" }
        switch task.type {
        case "continue_lesson": return "book.fill"
        case "mistake_review": return "exclamationmark.triangle.fill"
        case "mock_exam": return "checkmark.seal.fill"
        case "voice_dialog": return "mic.fill"
        default: return "rectangle.stack.fill"
        }
    }

    private func taskLabel(_ task: IOSCourseTodayTask) -> LocalizedStringKey {
        switch task.type {
        case "continue_lesson": return "today_task_lesson"
        case "mistake_review": return "today_task_mistakes"
        case "mock_exam": return "today_task_test"
        case "voice_dialog": return "today_task_voice"
        default: return "today_task_drill"
        }
    }
}

private struct CourseUnitCard: View {
    let unit: IOSCourseUnit
    let language: String
    let onOpenLesson: (IOSCourseLesson) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text(unit.title.value(language: language))
                    .font(.headline).foregroundStyle(HSKColors.ink)
                Spacer()
                Text("\(unit.lessons.filter { $0.status == "done" }.count)/\(unit.lessons.count)")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
            }

            ForEach(unit.lessons) { lesson in
                CourseLessonRow(
                    lesson: lesson,
                    language: language,
                    onOpen: { onOpenLesson(lesson) }
                )
            }
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .stroke(Color.white.opacity(0.50), lineWidth: 0.9)
        )
        .shadow(color: Color.black.opacity(0.07), radius: 14, y: 7)
    }
}

private struct CourseLessonRow: View {
    let lesson: IOSCourseLesson
    let language: String
    let onOpen: () -> Void

    var body: some View {
        Button(action: onOpen) {
        HStack(spacing: 12) {
            Image(systemName: statusIcon)
                .font(.title3)
                .foregroundStyle(statusColor)
                .frame(width: 30)

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 7) {
                    if !lesson.hanzi.isEmpty {
                        Text(lesson.hanzi).font(.headline).foregroundStyle(HSKColors.ink)
                    }
                    if !lesson.pinyin.isEmpty {
                        Text(lesson.pinyin).font(.caption).foregroundStyle(HSKColors.inkSecondary)
                    }
                }
                Text(lesson.subtitle.value(language: language))
                    .font(.subheadline)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .lineLimit(2)
            }

            Spacer()

            if lesson.partCount > 1 {
                Text("\(lesson.part)/\(lesson.partCount)")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(HSKColors.inkSecondary)
            }
        }
        .padding(.vertical, 6)
        .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!canOpen)
        .opacity(canOpen ? 1 : 0.58)
    }

    private var canOpen: Bool {
        let status = lesson.status.lowercased()
        return status == "current"
            || status == "done"
            || (lesson.completionAllowed && status != "locked")
    }

    private var statusIcon: String {
        switch lesson.status.lowercased() {
        case "done": return "checkmark.circle.fill"
        case "current": return "play.circle.fill"
        default: return (lesson.adUnlockable ?? false) ? "play.rectangle.fill" : "lock.circle.fill"
        }
    }

    private var statusColor: Color {
        switch lesson.status.lowercased() {
        case "done": return HSKColors.jade
        case "current": return HSKColors.cinnabar
        default: return HSKColors.inkSecondary
        }
    }
}
