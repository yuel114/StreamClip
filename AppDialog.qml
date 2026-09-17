import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Dialog {
    id: dialog
    property bool destructive: false
    padding: 22
    topPadding: 8
    spacing: 14
    background: Rectangle {
        radius: 20
        color: uiTheme.current.colors.dialog
        RectangularShadow {
            anchors.fill: parent
            z: -1
            radius: 20
            blur: 32
            offset: Qt.vector2d(0, 10)
            color: uiTheme.current.colors.shadow
        }
    }
    header: Label {
        text: dialog.title
        textFormat: Text.PlainText
        font.pixelSize: 18
        font.weight: Font.DemiBold
        color: uiTheme.current.colors.ink
        padding: 22
        bottomPadding: 12
        wrapMode: Text.Wrap
    }
    footer: DialogButtonBox {
        visible: count > 0
        padding: 18
        topPadding: 8
        spacing: 8
        alignment: Qt.AlignRight
        background: null
        delegate: ActionButton {
            readonly property bool accepting: DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole || DialogButtonBox.buttonRole === DialogButtonBox.YesRole
            primary: accepting && !dialog.destructive
            destructive: accepting && dialog.destructive
        }
    }
    Overlay.modal: Rectangle { color: uiTheme.current.colors.scrim }
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.motionEnabled && !uiTheme.transitioning ? 160 : 0; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: bridge.motionEnabled && !uiTheme.transitioning ? 180 : 0; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: bridge.motionEnabled && !uiTheme.transitioning ? 100 : 0 }
    }
}
