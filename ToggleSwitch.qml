import QtQuick
import QtQuick.Controls

Switch {
    id: control
    padding: 0
    spacing: 12
    implicitHeight: Math.max(36, implicitContentHeight)
    indicator: Rectangle {
        implicitWidth: 42
        implicitHeight: 24
        x: control.mirrored ? control.width - width : 0
        y: (control.height - height) / 2
        radius: 12
        color: !control.enabled ? uiTheme.current.colors.switchDisabled : control.checked ? uiTheme.current.colors.primary : uiTheme.current.colors.switchOff
        border.width: control.activeFocus ? 2 : 0
        border.color: uiTheme.current.colors.selectionInk
        Behavior on color { ColorAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 120 : 0 } }
        Rectangle {
            width: 20
            height: 20
            radius: 10
            x: 2 + control.visualPosition * 18
            y: 2
            color: control.enabled ? uiTheme.current.colors.control : uiTheme.current.colors.disabled
            Behavior on x { enabled: !control.down; NumberAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 160 : 0; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Text {
        text: control.text
        textFormat: Text.PlainText
        font: control.font
        color: control.enabled ? uiTheme.current.colors.ink : uiTheme.current.colors.disabledInk
        leftPadding: control.mirrored ? 0 : control.indicator.width + control.spacing
        rightPadding: control.mirrored ? control.indicator.width + control.spacing : 0
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.Wrap
    }
}
