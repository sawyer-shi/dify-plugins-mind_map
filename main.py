import io
import os

from dify_plugin import DifyPluginEnv, Plugin


def _warm_up_renderer():
    try:
        from tools.mpl_compat import import_matplotlib_agg

        import_matplotlib_agg()
        import matplotlib.pyplot as plt
        from PIL import ImageFont

        buf = io.BytesIO()
        fig = plt.figure(figsize=(0.2, 0.2), dpi=20)
        fig.savefig(buf, format="png", dpi=20)
        plt.close(fig)

        font_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansSC-Regular.otf"
        )
        ImageFont.truetype(font_path, 12).getbbox("测")
    except Exception:
        pass


_warm_up_renderer()

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
