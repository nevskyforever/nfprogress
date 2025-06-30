import Foundation

extension Notification.Name {
    /// Отправляется при изменении прогресса проекта. В объекте уведомления
    /// передаётся идентификатор проекта типа ``UUID``.
    static let projectProgressChanged = Notification.Name("projectProgressChanged")
    static let menuAddProject = Notification.Name("menuAddProject")
    static let menuAddEntry = Notification.Name("menuAddEntry")
    static let menuAddStage = Notification.Name("menuAddStage")
    static let menuImport = Notification.Name("menuImport")
    static let menuExport = Notification.Name("menuExport")
}
