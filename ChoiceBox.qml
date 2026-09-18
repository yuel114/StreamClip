import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl

ComboBox {
    id: control
    implicitHeight: 40
    padding: 6
    rightPadding: 30
    palette.mid: uiTheme.current.colors.choicePressed
    palette.buttonText: enabled ? uiTheme.current.colors.ink : uiTheme.current.colors.disabledInk
    background: Rectangle {
        radius: 10
        color: !control.enabled ? uiTheme.current.colors.disabled : control.down ? uiTheme.current.colors.choicePressed : uiTheme.current.colors.surface
        border.color: control.activeFocus ? uiTheme.current.colors.primary : uiTheme.current.colors.fieldBorder
        border.width: control.activeFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 110 : 0 } }
    }
    indicator: IconImage {
        objectName: control.objectName + "Indicator"
        source: artRoot + "icons/chevron-down.svg"
        width: 16; height: 16
        x: control.width - width - 10
        y: (control.height - height) / 2
        color: control.enabled ? uiTheme.current.colors.ink : uiTheme.current.colors.disabledInk
        rotation: control.popup.visible ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: bridge.motionEnabled && !uiTheme.transitioning ? 150 : 0; easing.type: Easing.OutCubic } }
    }
    delegate: ItemDelegate {
        required property var model
        required property int index
        width: ListView.view.width
        text: model[control.textRole]
        font.weight: control.currentIndex === index ? Font.DemiBold : Font.Normal
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled
        palette.text: control.palette.text
        // Qt Basic 用 light/midlight 绘制选项；不改编辑选择和焦点的 highlight。
        palette.light: uiTheme.current.colors.selection
        palette.midlight: uiTheme.current.colors.choicePressed
        palette.highlightedText: uiTheme.current.colors.selectionInk
        background: Rectangle {
            radius: 7
            color: parent.down ? uiTheme.current.colors.choicePressed : parent.highlighted ? uiTheme.current.colors.selection : "transparent"
        }
    }
    popup: Popup {
        y: control.height + 5
        width: control.width
        padding: 5
        margins: 8
        height: Math.min(contentItem.implicitHeight + 10, control.Window.height - 24)
        background: Rectangle { radius: 12; color: uiTheme.current.colors.surface; border.color: uiTheme.current.colors.fieldBorder }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            highlightMoveDuration: 0
            spacing: 2
            ScrollBar.vertical: ScrollBar {}
        }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.motionEnabled && !uiTheme.transitioning ? 120 : 0 } }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: bridge.motionEnabled && !uiTheme.transitioning ? 80 : 0 } }
    }
}
