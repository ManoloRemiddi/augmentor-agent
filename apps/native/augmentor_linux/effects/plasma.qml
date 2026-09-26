// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import QtQuick

ShaderEffect {
    id: effect
    property vector2d logicalSize: Qt.vector2d(1, 1)
    property vector4d surface: Qt.vector4d(0, 0, 1, 1)
    property vector4d tint: Qt.vector4d(1, 1, 1, 1)
    property vector4d frameState: Qt.vector4d(0, 0.5, 0, 20)
    property vector4d eruption: Qt.vector4d(0, 0, 1, 1)
    property vector2d eruptionState: Qt.vector2d(0, 0)
    property string noiseSource: "image://plasma/noise"
    property string flowSource: ""
    property string baseSource: ""
    property bool failed: status === ShaderEffect.Error
    property variant noiseTexture: Image {
        source: effect.noiseSource
        cache: false
        visible: false
        smooth: false
    }
    property variant flowTexture: Image {
        source: effect.flowSource
        visible: false
        cache: false
        smooth: true
    }
    property variant baseTexture: Image {
        source: effect.baseSource
        visible: false
        cache: false
        smooth: true
    }
    fragmentShader: "plasma.frag.qsb"
}
