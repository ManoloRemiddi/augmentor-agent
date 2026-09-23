# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded frame acquisition that distinguishes terminal stream failures."""
import time
import gi

gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst


def receive_frame(pipeline, cancel, timeout=10):
    """Read one frame; callers own pipeline teardown and observation invalidation."""
    if cancel.is_set():
        raise RuntimeError('Desktop control stopped.')
    if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        raise RuntimeError('The screen capture stream could not start. No input was sent.')
    sink = pipeline.get_by_name('capture')
    bus = pipeline.get_bus()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cancel.is_set():
            raise RuntimeError('Desktop control stopped.')
        sample = sink.emit('try-pull-sample', 100 * Gst.MSECOND)
        if cancel.is_set():
            raise RuntimeError('Desktop control stopped.')
        failure = bus.pop_filtered(Gst.MessageType.ERROR)
        if failure is not None:
            error, _debug = failure.parse_error()
            # Report the error category without exposing pipeline debug strings.
            raise RuntimeError(f'The screen capture stream failed ({error.domain}:{error.code}). No input was sent.')
        if sample is not None:
            buffer = sample.get_buffer()
            if buffer is None or buffer.get_size() == 0 or buffer.has_flags(Gst.BufferFlags.CORRUPTED):
                raise RuntimeError('The screen capture stream returned an invalid frame. No input was sent.')
            return sample
        if sink.get_property('eos'):
            raise RuntimeError('The screen capture stream ended without a frame. No input was sent.')
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
    raise RuntimeError('No screen frame was received before the capture timeout. No input was sent.')


def rgb_frame_layout(caps, mapped_size):
    """Validate the complete padded RGB buffer before passing it to Qt."""
    if caps is None or not caps.is_fixed() or caps.get_size() != 1:
        raise RuntimeError('The screen frame has invalid dimensions. No input was sent.')
    layout = caps.get_structure(0)
    width, height = layout.get_value('width'), layout.get_value('height')
    if (layout.get_name() != 'video/x-raw' or layout.get_value('format') != 'RGB'
            or type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0):
        raise RuntimeError('The screen frame has invalid dimensions or format. No input was sent.')
    stride = (width * 3 + 3) & ~3
    if mapped_size < stride * height:
        raise RuntimeError('The screen capture stream returned an incomplete frame. No input was sent.')
    return width, height, stride
