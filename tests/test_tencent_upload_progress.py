import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from patchright.async_api import async_playwright

from uploader.tencent_uploader.main import TencentUploadStalledError, TencentVideo


class UploadProgressTests(unittest.TestCase):
    def test_visible_progress_stalls_but_disabled_form_is_not_transport(self):
        async def scenario():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, channel="chrome")
                page = await browser.new_page()
                video = TencentVideo("测试", "unused.mp4", [], 0, "unused.json")
                video.save_upload_diagnostic = AsyncMock()
                await page.set_content('''
                    <div class="media-status-content"><span class="ant-progress-text">60%</span></div>
                    <div class="form-btns"><button class="weui-desktop-btn_disabled">发表</button></div>
                ''')
                with self.assertRaises(TencentUploadStalledError):
                    await video.wait_for_upload_complete(page, timeout_seconds=5, stall_timeout_seconds=0.01)
                self.assertEqual(video.save_upload_diagnostic.call_args.args[1]["progress_percent"], 60)
                # 复现第 71 首：百分比消失，但媒体区仍显示“取消上传”。
                await page.set_content('''
                    <div class="media-status-content">
                        <span class="ant-progress-text">75%</span>
                        <div class="tag-inner">取消上传</div>
                    </div>
                    <div class="form-btns"><button class="weui-desktop-btn_disabled">发表</button></div>
                ''')
                waiting = asyncio.create_task(video.wait_for_upload_complete(
                    page, timeout_seconds=5, stall_timeout_seconds=0.1))
                await page.wait_for_timeout(50)
                await page.locator(".ant-progress-text").evaluate("node => node.remove()")
                with self.assertRaises(TencentUploadStalledError):
                    await waiting
                state = video.save_upload_diagnostic.call_args.args[1]
                self.assertIsNone(state["progress_percent"])
                self.assertTrue(state["upload_active"])
                self.assertEqual(state["phase"], "transferring")
                await page.locator(".media-status-content").evaluate("node => node.remove()")
                with self.assertRaises(RuntimeError) as result:
                    await video.wait_for_upload_complete(page, timeout_seconds=0, stall_timeout_seconds=0.01)
                self.assertNotIsInstance(result.exception, TencentUploadStalledError)
                await page.locator("button").evaluate("node => node.className = ''")
                await video.wait_for_upload_complete(page)
                await browser.close()

        asyncio.run(scenario())

    def test_only_one_pre_submit_media_recovery(self):
        async def scenario(failures, submit_error, expected_sessions, expected_submits):
            video = TencentVideo("测试", "unused.mp4", [], 0, "unused.json")
            for method in ("validate_upload_args", "open_upload_page", "upload_video_file",
                           "prepare_video_for_publish", "apply_collection", "apply_original_statement",
                           "set_thumbnail", "set_short_title"):
                setattr(video, method, AsyncMock())
            video.wait_for_upload_complete = AsyncMock(side_effect=failures)
            video.submit_publish = AsyncMock(side_effect=submit_error)
            contexts = []

            async def make_browser(**kwargs):
                context = Mock(new_page=AsyncMock(return_value=Mock()), close=AsyncMock(), storage_state=AsyncMock())
                contexts.append(context)
                return Mock(new_context=AsyncMock(return_value=context), close=AsyncMock())

            playwright = Mock(chromium=Mock(launch=AsyncMock(side_effect=make_browser)))
            try:
                await video.upload(playwright)
            except RuntimeError:
                self.assertTrue(submit_error or len(failures) == 2 and failures[-1])
            else:
                self.assertFalse(submit_error)
                self.assertIsNone(failures[-1])
            self.assertEqual(len(contexts), expected_sessions)
            self.assertEqual(video.submit_publish.await_count, expected_submits)
            for context in contexts:
                context.close.assert_awaited_once()

        for failures, submit_error, sessions, submits in (
            ([TencentUploadStalledError("停滞"), None], None, 2, 1),
            ([TencentUploadStalledError("停滞"), TencentUploadStalledError("再次停滞")], None, 2, 0),
            ([None], RuntimeError("提交结果不明"), 1, 1),
        ):
            with self.subTest(sessions=sessions, submits=submits):
                asyncio.run(scenario(failures, submit_error, sessions, submits))


if __name__ == "__main__":
    unittest.main()
