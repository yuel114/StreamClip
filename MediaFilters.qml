import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: filters
    required property var library
    required property string namePrefix
    property var state: library.filters
    property var availableDates: {
        const dates = {}
        for (const day of state.dates) dates[day] = true
        return dates
    }
    spacing: 8
    onVisibleChanged: if (!visible) calendar.close()

    Label { text: "主播" }
    ChoiceBox {
        id: streamer
        objectName: filters.namePrefix + "StreamerFilter"
        Layout.fillWidth: true
        Layout.minimumWidth: 150
        Layout.preferredWidth: 240
        Layout.maximumWidth: 320
        implicitHeight: 40
        model: filters.state.streamers
        textRole: "label"
        valueRole: "key"
        currentIndex: {
            for (let i = 0; i < model.length; ++i)
                if (model[i].key === filters.state.streamer) return i
            return 0
        }
        Accessible.name: "按主播筛选"
        onActivated: filters.library.setFilter(currentValue, "")
        ToolTip.visible: hovered && currentText.length > 12
        ToolTip.text: currentText
    }
    Label { text: "录播日期"; Layout.leftMargin: 8 }
    ActionButton {
        id: dateButton
        objectName: filters.namePrefix + "DateFilter"
        Layout.preferredWidth: 156
        text: filters.state.date || "全部日期"
        symbol: "calendar"
        Accessible.name: "打开录播日期日历，当前" + text
        onClicked: calendar.open()
        ToolTip.visible: hovered && !calendar.visible
        ToolTip.text: "按原录播的开始日期归类；导入媒体使用导入日期。"
    }
    Popup {
        id: calendar
        objectName: filters.namePrefix + "Calendar"
        // 由 Qt 跟踪按钮及其父布局的位置，并在窗口边缘自动避让。
        parent: dateButton
        x: 0
        y: dateButton.height + 6
        margins: 8
        width: 360
        padding: 12
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        property int viewYear: new Date().getFullYear()
        property int viewMonth: 0
        property string openedStreamer: ""
        function choose(day) {
            if (day && !filters.availableDates[day]) return
            filters.library.setFilter(filters.state.streamer, day)
            close()
        }
        function changeMonth(offset) {
            const month = viewYear * 12 + viewMonth + offset
            if (month < 12 || month >= 120000) return
            viewYear = Math.floor(month / 12)
            viewMonth = month % 12
        }
        onAboutToShow: {
            openedStreamer = filters.state.streamer
            const days = filters.state.dates.filter(day => /^\d{4}-\d{2}-\d{2}$/.test(day))
            const day = /^\d{4}-\d{2}-\d{2}$/.test(filters.state.date) ? filters.state.date : days[0] || Qt.formatDate(new Date(), "yyyy-MM-dd")
            viewYear = Number(day.slice(0, 4))
            viewMonth = Number(day.slice(5, 7)) - 1
        }
        onClosed: if (dateButton.visible) dateButton.forceActiveFocus()
        background: Rectangle { radius: 16; color: uiTheme.current.colors.surface; border.color: uiTheme.current.colors.fieldBorder }
        contentItem: ColumnLayout {
            spacing: 8
            RowLayout {
                spacing: 6
                ActionButton {
                    objectName: filters.namePrefix + "PreviousMonth"
                    text: "上月"
                    symbol: "chevron-left"
                    display: AbstractButton.IconOnly
                    flat: true
                    Accessible.name: "上一个月"
                    enabled: calendar.viewYear > 1 || calendar.viewMonth > 0
                    onClicked: calendar.changeMonth(-1)
                }
                SpinBox {
                    objectName: filters.namePrefix + "CalendarYear"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 128
                    from: 1; to: 9999; editable: true
                    value: calendar.viewYear
                    textFromValue: function(value, locale) { return String(value) }
                    valueFromText: function(text, locale) { return Number(text) }
                    Accessible.name: "年份，可直接输入"
                    onValueModified: calendar.viewYear = value
                }
                ChoiceBox {
                    objectName: filters.namePrefix + "CalendarMonth"
                    Layout.preferredWidth: 80
                    model: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
                    currentIndex: calendar.viewMonth
                    Accessible.name: "月份"
                    onActivated: calendar.viewMonth = currentIndex
                }
                ActionButton {
                    objectName: filters.namePrefix + "NextMonth"
                    text: "下月"
                    symbol: "chevron-right"
                    display: AbstractButton.IconOnly
                    flat: true
                    Accessible.name: "下一个月"
                    enabled: calendar.viewYear < 9999 || calendar.viewMonth < 11
                    onClicked: calendar.changeMonth(1)
                }
            }
            DayOfWeekRow { Layout.fillWidth: true; locale: Qt.locale("zh_CN") }
            MonthGrid {
                id: monthGrid
                objectName: filters.namePrefix + "CalendarGrid"
                Layout.fillWidth: true
                Layout.preferredHeight: 228
                month: calendar.viewMonth
                year: calendar.viewYear
                locale: Qt.locale("zh_CN")
                spacing: 4
                delegate: ItemDelegate {
                    id: dayButton
                    required property var model
                    property string dayKey: Qt.formatDate(model.date, "yyyy-MM-dd")
                    property bool inMonth: model.month === monthGrid.month
                    highlighted: dayKey === filters.state.date
                    // 保留邻月格子的占位，否则 Grid 会把每月 1 日都排到周一。
                    opacity: inMonth ? 1 : 0
                    enabled: inMonth && !!filters.availableDates[dayKey]
                    font.bold: enabled
                    Accessible.ignored: !inMonth
                    Accessible.name: Qt.formatDate(model.date, "yyyy年M月d日") + (enabled ? "，有内容" : "，无内容")
                    onClicked: calendar.choose(dayKey)
                    contentItem: Text {
                        text: dayButton.model.day
                        font: dayButton.font
                        color: dayButton.highlighted ? uiTheme.current.colors.onPrimary : dayButton.enabled ? uiTheme.current.colors.ink : uiTheme.current.colors.unavailable
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 8
                        color: dayButton.highlighted ? uiTheme.current.colors.primary : dayButton.hovered && dayButton.enabled ? uiTheme.current.colors.selection : "transparent"
                        border.width: dayButton.activeFocus ? 2 : dayButton.model.today ? 1 : 0
                        border.color: uiTheme.current.colors.primary
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 3
                            width: 4; height: 4; radius: 2
                            color: dayButton.highlighted ? uiTheme.current.colors.onPrimary : uiTheme.current.colors.primary
                            visible: dayButton.enabled
                        }
                    }
                }
            }
            Label { text: "带圆点的日期有内容，年份可直接输入。"; color: uiTheme.current.colors.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                ActionButton { objectName: filters.namePrefix + "AllDates"; text: "全部日期"; onClicked: calendar.choose("") }
                ActionButton { objectName: filters.namePrefix + "UnknownDate"; text: "日期未知"; visible: !!filters.availableDates["日期未知"]; onClicked: calendar.choose("日期未知") }
                Item { Layout.fillWidth: true }
            }
        }
    }
    Connections {
        target: filters.library
        function onFiltersChanged() {
            if (calendar.visible && calendar.openedStreamer !== filters.state.streamer) calendar.close()
        }
    }
    ActionButton {
        objectName: filters.namePrefix + "ResetFilters"
        text: "重置"
        symbol: "rotate-ccw"
        display: AbstractButton.IconOnly
        flat: true
        enabled: !!filters.state.streamer || !!filters.state.date
        onClicked: filters.library.setFilter("", "")
    }
    Item { Layout.fillWidth: true }
    Label { text: filters.state.count + " / " + filters.state.total + " 条"; color: uiTheme.current.colors.muted }
}
