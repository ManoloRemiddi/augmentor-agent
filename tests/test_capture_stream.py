# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real GStreamer frame, EOS, startup failure and cancellation checks."""
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/desktop'))
try:
    from capture_stream import Gst, receive_frame, rgb_frame_layout
except (ImportError, ValueError) as error:
    raise unittest.SkipTest('GStreamer introspection is unavailable: '+str(error))


class CaptureStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Gst.init(None)
        if not Gst.ElementFactory.find("videotestsrc") or not Gst.ElementFactory.find("appsink"):
            raise unittest.SkipTest("GStreamer test-source and app plugins are required")

    def pipeline(self, description):
        pipeline = Gst.parse_launch(description)
        self.addCleanup(pipeline.set_state, Gst.State.NULL)
        return pipeline

    def test_frame(self):
        pipeline = self.pipeline('videotestsrc num-buffers=1 ! appsink name=capture')
        self.assertIsNotNone(receive_frame(pipeline, threading.Event()).get_buffer())

    def test_eos_without_frame(self):
        pipeline = self.pipeline('videotestsrc num-buffers=0 ! appsink name=capture')
        with self.assertRaisesRegex(RuntimeError, 'ended without a frame'):
            receive_frame(pipeline, threading.Event())

    def test_invalid_buffer(self):
        for size, corrupted in ((0, False), (12, True)):
            with self.subTest(size=size, corrupted=corrupted):
                pipeline = self.pipeline('appsrc name=source is-live=true ! appsink name=capture sync=false')
                source = pipeline.get_by_name('source')
                source.set_property('caps', Gst.Caps.from_string('video/x-raw,format=RGB,width=2,height=2,framerate=1/1'))
                buffer = Gst.Buffer.new_allocate(None, size, None)
                if corrupted:
                    buffer.set_flags(Gst.BufferFlags.CORRUPTED)
                self.assertEqual(source.emit('push-buffer', buffer), Gst.FlowReturn.OK)
                with self.assertRaisesRegex(RuntimeError, 'invalid frame'):
                    receive_frame(pipeline, threading.Event())

    def test_rgb_rows_include_padding_and_reject_truncated_samples(self):
        pipeline = self.pipeline('appsrc name=source is-live=true ! appsink name=capture sync=false')
        source = pipeline.get_by_name('source')
        caps = Gst.Caps.from_string('video/x-raw,format=RGB,width=2,height=2,framerate=1/1')
        source.set_property('caps', caps)
        # Twelve bytes hold the pixels, but not the two padded eight-byte rows.
        source.emit('push-buffer', Gst.Buffer.new_allocate(None, 12, None))
        sample = receive_frame(pipeline, threading.Event())
        buffer = sample.get_buffer()
        ok, mapping = buffer.map(Gst.MapFlags.READ)
        self.assertTrue(ok)
        try:
            with self.assertRaisesRegex(RuntimeError, 'incomplete frame'):
                rgb_frame_layout(sample.get_caps(), len(mapping.data))
        finally:
            buffer.unmap(mapping)
        self.assertEqual(rgb_frame_layout(caps, 16), (2, 2, 8))

    def test_invalid_rgb_layout(self):
        for caps in (None, Gst.Caps.from_string('video/x-raw,format=I420,width=2,height=2'),
                     Gst.Caps.from_string('video/x-raw,format=RGB,width=0,height=2'),
                     Gst.Caps.from_string('video/x-raw,format=RGB,width=2')):
            with self.subTest(caps=caps), self.assertRaisesRegex(RuntimeError, 'invalid dimensions'):
                rgb_frame_layout(caps, 1024)

    def test_failed_start(self):
        pipeline = self.pipeline('filesrc location=/nonexistent-augmentor-capture-fixture ! appsink name=capture')
        with self.assertRaisesRegex(RuntimeError, 'could not start|stream failed'):
            receive_frame(pipeline, threading.Event())

    def test_stream_error(self):
        pipeline = self.pipeline('videotestsrc is-live=true ! identity error-after=1 ! appsink name=capture')
        with self.assertRaisesRegex(RuntimeError, 'stream failed'):
            receive_frame(pipeline, threading.Event())

    def test_timeout_without_frame(self):
        pipeline = self.pipeline('appsrc is-live=true ! appsink name=capture')
        with self.assertRaisesRegex(RuntimeError, 'capture timeout'):
            receive_frame(pipeline, threading.Event(), timeout=.2)

    def test_cancel_while_waiting(self):
        pipeline = self.pipeline('appsrc is-live=true ! appsink name=capture')
        cancel = threading.Event()
        timer = threading.Timer(.05, cancel.set)
        timer.start(); self.addCleanup(timer.cancel)
        with self.assertRaisesRegex(RuntimeError, 'stopped'):
            receive_frame(pipeline, cancel)

    def test_cancelled(self):
        pipeline = self.pipeline('videotestsrc ! appsink name=capture')
        cancel = threading.Event(); cancel.set()
        with self.assertRaisesRegex(RuntimeError, 'stopped'):
            receive_frame(pipeline, cancel)


if __name__ == '__main__':
    unittest.main()
