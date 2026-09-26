// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 logicalSize;
    vec4 surface;
    vec4 tint;
    vec4 frameState;
    vec4 eruption;
    vec2 eruptionState;
} ub;
layout(binding = 1) uniform sampler2D noiseTexture;
layout(binding = 2) uniform sampler2D flowTexture;
layout(binding = 3) uniform sampler2D baseTexture;

float cell(ivec2 p) {
    vec2 encoded = texelFetch(noiseTexture, p & ivec2(127), 0).rg;
    return dot(encoded, vec2(65280.0, 255.0)) / 65535.0;
}
float noise(vec2 p) {
    ivec2 i = ivec2(floor(p));
    vec2 f = fract(p);
    return mix(mix(cell(i), cell(i + ivec2(1, 0)), f.x),
               mix(cell(i + ivec2(0, 1)), cell(i + ivec2(1, 1)), f.x), f.y);
}
float roundedDistance(vec2 p, vec4 rect, float radius) {
    vec2 q = abs(p - rect.xy - rect.zw * 0.5) - (rect.zw * 0.5 - radius);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}
void main() {
    vec2 p = qt_TexCoord0 * ub.logicalSize;
    float signedDistance = roundedDistance(p, ub.surface, ub.frameState.w);
    float aa = max(fwidth(signedDistance), 0.01);
    float coverage = smoothstep(-aa * 0.5, aa * 0.5, signedDistance);
    float distance = max(0.0, signedDistance);
    float fade = clamp(min(min(p.x, p.y), min(ub.logicalSize.x-p.x, ub.logicalSize.y-p.y)) / 20.0, 0.0, 1.0);
    float t = ub.frameState.x;
    float breath = ub.frameState.y;
    float alpha = 0.0;
    float fine = 0.4;
    float ridge = 0.0;
    if (distance < 64.0) {
        vec2 pos = p * 0.075;
        float q = noise(pos * 0.43 + vec2(t * 1.65, -t * 0.95));
        float r = noise(pos * 0.39 + vec2(-t * 1.1 + 37.0, t * 1.45 + 71.0));
        vec2 warped = pos + 16.0 * vec2(q, r);
        float cloud = noise(warped + vec2(t * 1.7, -t * 2.1));
        fine = noise(warped * 1.6 + vec2(-t * 2.2 + 19.0, t * 0.85));
        ridge = pow(max(0.0, 1.0 - abs(cloud + 0.16 * fine - 0.58) * 6.0), 2.0);
        float localBreath = 0.7 + 0.6 * noise(pos * 0.6 + vec2(t * 0.8 + 81.0, -t * 0.5));
        float reach = 5.0 + 29.0 * q * localBreath;
        float envelope = exp(-pow(distance / reach, 2.0) * 1.9) * fade;
        alpha = envelope * (0.025 + 0.19 * cloud + 0.55 * ridge) * (0.65 + 0.65 * breath) * localBreath;
    }
    float flareLight = 0.0;
    if (ub.eruptionState.y > 0.5) {
        int side = int(ub.eruption.x);
        float tangent = ((side == 0 || side == 2) ? p.x : p.y) - ub.eruption.y;
        float normal = side == 0 ? ub.surface.y-p.y : side == 1 ? p.x-ub.surface.x-ub.surface.z : side == 2 ? p.y-ub.surface.y-ub.surface.w : ub.surface.x-p.x;
        float width = ub.eruption.z;
        if (normal >= -2.0 && abs(tangent) < width * 2.5) {
            float height = max(1.0, ub.eruption.w);
            float fraction = clamp(normal / height, 0.0, 1.0);
            float bend = height * 0.13 * sin(3.14159265359 * fraction) *
                         (sin(fraction * 4.7 + t * 1.4) + 0.35 * sin(fraction * 9.1 - t * 2.1));
            float radius = width * 0.65 * sqrt(max(0.0, 1.0 - fraction));
            float strandWidth = 1.6 + 4.8 * pow(1.0 - fraction, 1.5);
            vec2 edges = vec2(tangent-bend-radius, tangent-bend+radius*0.82) / strandWidth;
            float strands = exp(-edges.x*edges.x) + 0.8*exp(-edges.y*edges.y);
            float cap = exp(-pow(max(0.0, normal-height)/strandWidth, 2.0));
            float detail = 0.65 + 0.35 * noise(vec2(normal*0.18+t*1.7, tangent*0.08-t*1.1+23.0));
            float density = (1.0-0.72*fraction)*exp(-max(0.0, normal)/160.0);
            float root = exp(-pow(tangent/(width*0.7), 2.0)-pow(normal/12.0, 2.0))*0.35;
            flareLight = (strands*cap*density*detail+root)*ub.eruptionState.x*fade;
            alpha += flareLight * 0.75;
        }
    }
    float light = 0.66 + 0.28*fine + 0.35*ridge + 0.4*flareLight;
    float desaturate = flareLight > 0.0 ? clamp((distance-16.0)/192.0, 0.0, 0.78) : 0.0;
    float grey = dot(ub.tint.rgb, vec3(1.0/3.0));
    vec3 colour = clamp(mix(ub.tint.rgb, vec3(grey), desaturate)*light, 0.0, 1.0);
    alpha = clamp(alpha, 0.0, 200.0/255.0);
    vec4 emission = vec4(colour*alpha, alpha);
    // Transport broad smoke on the CPU grid; resolve every fine strand in the
    // native display backing store. All terms are premultiplied before mixing.
    vec4 result = clamp(texture(flowTexture, qt_TexCoord0) + emission - texture(baseTexture, qt_TexCoord0), 0.0, 1.0);
    result.rgb = min(result.rgb, vec3(result.a));
    fragColor = result * coverage * ub.frameState.z * ub.qt_Opacity;
}
