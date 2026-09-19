import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: versions
    objectName: "versionPage"
    spacing: 12
    property var info: bridge.updateInfo
    signal installRequested(string version)
    readonly property bool working: ["checking", "downloading", "installing"].indexOf(info.state) >= 0

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Label { text: "StreamClip  " + versions.info.currentVersion; font.pixelSize: 22; font.weight: Font.DemiBold }
            Label {
                text: "当前版本" + (versions.info.sourceBuild ? " · 源码运行" : " · Windows x64")
                color: uiTheme.current.colors.muted
                font.pixelSize: 12
            }
        }
        ActionButton {
            objectName: "checkUpdatesButton"
            text: versions.info.state === "checking" ? "检查中…" : "检查新版本"
            symbol: "refresh-cw"
            enabled: !versions.working && !bridge.busy
            onClicked: bridge.checkUpdates()
        }
        ActionButton {
            objectName: "downloadUpdateButton"
            text: versions.info.state === "ready" ? "安装并重启" : "下载更新"
            symbol: versions.info.state === "ready" ? "rotate-ccw" : "download"
            primary: true
            visible: versions.info.canDownload
            enabled: !versions.working && !bridge.busy
            onClicked: {
                if (versions.info.state === "ready") {
                    versions.installRequested(versions.info.latestVersion)
                } else bridge.downloadUpdate()
            }
        }
    }
    Label {
        objectName: "updateStatus"
        Layout.fillWidth: true
        text: versions.info.message
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: versions.info.hasUpdate ? uiTheme.current.colors.primary : uiTheme.current.colors.ink
        Accessible.role: Accessible.StaticText
    }
    Label {
        objectName: "updateError"
        Layout.fillWidth: true
        visible: !!text
        text: versions.info.error
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: uiTheme.current.colors.danger
    }
    RowLayout {
        Layout.fillWidth: true
        visible: versions.info.state === "downloading"
        ProgressBar {
            objectName: "updateProgress"
            Layout.fillWidth: true
            value: versions.info.progress
            Accessible.name: "更新下载进度"
        }
        Label {
            text: Math.floor(versions.info.progress * 100) + "%  ·  " + (versions.info.received / 1048576).toFixed(1) + " / " + (versions.info.total / 1048576).toFixed(1) + " MB"
            font.pixelSize: 12
            color: uiTheme.current.colors.muted
        }
        ActionButton { objectName: "cancelUpdateButton"; text: "取消下载"; onClicked: bridge.cancelUpdateDownload() }
    }
    RowLayout {
        Layout.fillWidth: true
        ToggleSwitch {
            objectName: "automaticUpdatesSwitch"
            text: "自动检查并提醒"
            checked: versions.info.autoCheck
            enabled: !bridge.busy
            onToggled: bridge.setAutomaticUpdates(checked)
        }
        Item { Layout.fillWidth: true }
        Label {
            text: versions.info.lastChecked ? "上次检查 " + versions.info.lastChecked : "尚无检查记录"
            color: uiTheme.current.colors.muted
            font.pixelSize: 12
        }
        ActionButton {
            objectName: "releasePageButton"
            text: "发布页面"
            symbol: "chevron-right"
            flat: true
            onClicked: Qt.openUrlExternally(versions.info.releaseUrl)
        }
    }
    Label {
        visible: versions.info.hasUpdate && !versions.info.canDownload
        Layout.fillWidth: true
        text: versions.info.sourceBuild ? "源码版请从发布页面下载新版本。" : "该版本暂未提供带 SHA-256 校验的 Windows x64 更新包，请查看发布页面。"
        wrapMode: Text.Wrap
        color: uiTheme.current.colors.warning
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 8
        Label { text: "历史版本"; font.weight: Font.DemiBold }
        Item { Layout.fillWidth: true }
        Label { text: versions.info.history.length + " 个版本"; font.pixelSize: 12; color: uiTheme.current.colors.muted }
    }
    ListView {
        id: history
        objectName: "releaseHistory"
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 0
        model: versions.info.history
        ScrollBar.vertical: ScrollBar {}
        delegate: Item {
            id: releaseRow
            required property var modelData
            property bool expanded: false
            width: history.width - 14
            implicitHeight: releaseContent.implicitHeight + 28
            ColumnLayout {
                id: releaseContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: 12
                spacing: 6
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "v" + releaseRow.modelData.version; font.weight: Font.DemiBold }
                    Label {
                        text: releaseRow.modelData.current ? "当前版本" : releaseRow.modelData.version === versions.info.latestVersion ? "最新正式版" : ""
                        visible: !!text
                        font.pixelSize: 12
                        color: uiTheme.current.colors.primary
                    }
                    Item { Layout.fillWidth: true }
                    Label { text: releaseRow.modelData.date; font.pixelSize: 12; color: uiTheme.current.colors.muted }
                    ActionButton {
                        text: releaseRow.expanded ? "收起更新说明" : "展开更新说明"
                        symbol: releaseRow.expanded ? "chevron-down" : "chevron-right"
                        display: AbstractButton.IconOnly
                        flat: true
                        implicitHeight: 32
                        onClicked: releaseRow.expanded = !releaseRow.expanded
                    }
                }
                Label {
                    Layout.fillWidth: true
                    visible: !releaseRow.expanded
                    text: releaseRow.modelData.summary
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: uiTheme.current.colors.ink
                }
                TextArea {
                    Layout.fillWidth: true
                    visible: releaseRow.expanded
                    text: releaseRow.modelData.notes
                    textFormat: TextEdit.PlainText
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: uiTheme.current.colors.ink
                    padding: 0
                    background: null
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: uiTheme.current.colors.controlBorder }
        }
    }
}
