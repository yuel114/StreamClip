import QtQuick
import QtQuick.Controls

Button {
    id: button
    property bool primary: false
    property bool destructive: false
    property string symbol: ""
    readonly property color foreground: !enabled ? uiTheme.current.colors.disabledInk : primary ? uiTheme.current.colors.onPrimary : destructive ? uiTheme.current.colors.danger : uiTheme.current.colors.ink
    padding: 8
    leftPadding: display === AbstractButton.IconOnly ? 10 : 14
    rightPadding: leftPadding
    implicitHeight: 40
    implicitWidth: Math.max(display === AbstractButton.IconOnly ? 36 : 0, implicitContentWidth + leftPadding + rightPadding)
    spacing: 7
    hoverEnabled: true
    font.weight: primary ? Font.DemiBold : Font.Normal
    icon.source: symbol ? artRoot + "icons/" + symbol + ".svg" : ""
    icon.width: 17
    icon.height: 17
    icon.color: foreground
    palette.buttonText: foreground
    palette.windowText: foreground
    palette.brightText: foreground
    scale: down && enabled ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 100 : 0; easing.type: Easing.OutCubic } }
    Accessible.name: text
    ToolTip.visible: hovered && display === AbstractButton.IconOnly
    ToolTip.text: text
    ToolTip.delay: 500
    background: Rectangle {
        radius: 10
        color: !button.enabled ? (button.flat ? "transparent" : uiTheme.current.colors.disabled) : button.primary ? (button.down ? uiTheme.current.colors.primaryPressed : button.hovered ? uiTheme.current.colors.primaryHover : uiTheme.current.colors.primary) : button.down ? uiTheme.current.colors.controlPressed : button.hovered ? uiTheme.current.colors.controlHover : button.flat ? "transparent" : uiTheme.current.colors.control
        border.color: button.activeFocus ? uiTheme.current.colors.primary : uiTheme.current.colors.controlBorder
        border.width: button.activeFocus ? 2 : button.primary || button.flat ? 0 : 1
        Behavior on color { ColorAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 110 : 0 } }
        Rectangle {
            objectName: "primaryFocusRing"
            anchors.fill: parent
            anchors.margins: 3
            radius: 7
            color: "transparent"
            border.width: 2
            border.color: uiTheme.current.colors.onPrimary
            visible: button.primary && button.activeFocus && button.enabled
        }
    }
}
