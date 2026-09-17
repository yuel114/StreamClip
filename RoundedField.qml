import QtQuick
import QtQuick.Controls

TextField {
    id: field
    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
    selectByMouse: true
    color: enabled ? uiTheme.current.colors.ink : uiTheme.current.colors.disabledInk
    placeholderTextColor: uiTheme.current.colors.placeholder
    background: Rectangle {
        radius: 10
        color: field.enabled ? uiTheme.current.colors.surface : uiTheme.current.colors.disabled
        border.color: field.activeFocus ? uiTheme.current.colors.primary : uiTheme.current.colors.fieldBorder
        border.width: field.activeFocus ? 2 : 1
        Behavior on border.color { ColorAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 120 : 0 } }
    }
}
