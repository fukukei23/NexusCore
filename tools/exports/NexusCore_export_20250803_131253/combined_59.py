
# === NexusCore/app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/src\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/src\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/src\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/tools\exports\export_20250803_114325\combined_48.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\axis.py ===
"""
Classes for the ticks and x- and y-axis.
"""

import datetime
import functools
import logging
from numbers import Real
import warnings

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook
import matplotlib.artist as martist
import matplotlib.colors as mcolors
import matplotlib.lines as mlines
import matplotlib.scale as mscale
import matplotlib.text as mtext
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import matplotlib.units as munits

_log = logging.getLogger(__name__)

GRIDLINE_INTERPOLATION_STEPS = 180

# This list is being used for compatibility with Axes.grid, which
# allows all Line2D kwargs.
_line_inspector = martist.ArtistInspector(mlines.Line2D)
_line_param_names = _line_inspector.get_setters()
_line_param_aliases = [next(iter(d)) for d in _line_inspector.aliasd.values()]
_gridline_param_names = ['grid_' + name
                         for name in _line_param_names + _line_param_aliases]


class Tick(martist.Artist):
    """
    Abstract base class for the axis ticks, grid lines and labels.

    Ticks mark a position on an Axis. They contain two lines as markers and
    two labels; one each for the bottom and top positions (in case of an
    `.XAxis`) or for the left and right positions (in case of a `.YAxis`).

    Attributes
    ----------
    tick1line : `~matplotlib.lines.Line2D`
        The left/bottom tick marker.
    tick2line : `~matplotlib.lines.Line2D`
        The right/top tick marker.
    gridline : `~matplotlib.lines.Line2D`
        The grid line associated with the label position.
    label1 : `~matplotlib.text.Text`
        The left/bottom tick label.
    label2 : `~matplotlib.text.Text`
        The right/top tick label.

    """
    def __init__(
        self, axes, loc, *,
        size=None,  # points
        width=None,
        color=None,
        tickdir=None,
        pad=None,
        labelsize=None,
        labelcolor=None,
        labelfontfamily=None,
        zorder=None,
        gridOn=None,  # defaults to axes.grid depending on axes.grid.which
        tick1On=True,
        tick2On=True,
        label1On=True,
        label2On=False,
        major=True,
        labelrotation=0,
        grid_color=None,
        grid_linestyle=None,
        grid_linewidth=None,
        grid_alpha=None,
        **kwargs,  # Other Line2D kwargs applied to gridlines.
    ):
        """
        bbox is the Bound2D bounding box in display coords of the Axes
        loc is the tick location in data coords
        size is the tick size in points
        """
        super().__init__()

        if gridOn is None:
            which = mpl.rcParams['axes.grid.which']
            if major and (which in ('both', 'major')):
                gridOn = mpl.rcParams['axes.grid']
            elif (not major) and (which in ('both', 'minor')):
                gridOn = mpl.rcParams['axes.grid']
            else:
                gridOn = False

        self.set_figure(axes.get_figure(root=False))
        self.axes = axes

        self._loc = loc
        self._major = major

        name = self.__name__
        major_minor = "major" if major else "minor"

        if size is None:
            size = mpl.rcParams[f"{name}.{major_minor}.size"]
        self._size = size

        if width is None:
            width = mpl.rcParams[f"{name}.{major_minor}.width"]
        self._width = width

        if color is None:
            color = mpl.rcParams[f"{name}.color"]

        if pad is None:
            pad = mpl.rcParams[f"{name}.{major_minor}.pad"]
        self._base_pad = pad

        if labelcolor is None:
            labelcolor = mpl.rcParams[f"{name}.labelcolor"]

        if cbook._str_equal(labelcolor, 'inherit'):
            # inherit from tick color
            labelcolor = mpl.rcParams[f"{name}.color"]

        if labelsize is None:
            labelsize = mpl.rcParams[f"{name}.labelsize"]

        self._set_labelrotation(labelrotation)

        if zorder is None:
            if major:
                zorder = mlines.Line2D.zorder + 0.01
            else:
                zorder = mlines.Line2D.zorder
        self._zorder = zorder

        grid_color = mpl._val_or_rc(grid_color, "grid.color")
        grid_linestyle = mpl._val_or_rc(grid_linestyle, "grid.linestyle")
        grid_linewidth = mpl._val_or_rc(grid_linewidth, "grid.linewidth")
        if grid_alpha is None and not mcolors._has_alpha_channel(grid_color):
            # alpha precedence: kwarg > color alpha > rcParams['grid.alpha']
            # Note: only resolve to rcParams if the color does not have alpha
            # otherwise `grid(color=(1, 1, 1, 0.5))` would work like
            #   grid(color=(1, 1, 1, 0.5), alpha=rcParams['grid.alpha'])
            # so the that the rcParams default would override color alpha.
            grid_alpha = mpl.rcParams["grid.alpha"]
        grid_kw = {k[5:]: v for k, v in kwargs.items()}

        self.tick1line = mlines.Line2D(
            [], [],
            color=color, linestyle="none", zorder=zorder, visible=tick1On,
            markeredgecolor=color, markersize=size, markeredgewidth=width,
        )
        self.tick2line = mlines.Line2D(
            [], [],
            color=color, linestyle="none", zorder=zorder, visible=tick2On,
            markeredgecolor=color, markersize=size, markeredgewidth=width,
        )
        self.gridline = mlines.Line2D(
            [], [],
            color=grid_color, alpha=grid_alpha, visible=gridOn,
            linestyle=grid_linestyle, linewidth=grid_linewidth, marker="",
            **grid_kw,
        )
        self.gridline.get_path()._interpolation_steps = \
            GRIDLINE_INTERPOLATION_STEPS
        self.label1 = mtext.Text(
            np.nan, np.nan,
            fontsize=labelsize, color=labelcolor, visible=label1On,
            fontfamily=labelfontfamily, rotation=self._labelrotation[1])
        self.label2 = mtext.Text(
            np.nan, np.nan,
            fontsize=labelsize, color=labelcolor, visible=label2On,
            fontfamily=labelfontfamily, rotation=self._labelrotation[1])

        self._apply_tickdir(tickdir)

        for artist in [self.tick1line, self.tick2line, self.gridline,
                       self.label1, self.label2]:
            self._set_artist_props(artist)

        self.update_position(loc)

    def _set_labelrotation(self, labelrotation):
        if isinstance(labelrotation, str):
            mode = labelrotation
            angle = 0
        elif isinstance(labelrotation, (tuple, list)):
            mode, angle = labelrotation
        else:
            mode = 'default'
            angle = labelrotation
        _api.check_in_list(['auto', 'default'], labelrotation=mode)
        self._labelrotation = (mode, angle)

    @property
    def _pad(self):
        return self._base_pad + self.get_tick_padding()

    def _apply_tickdir(self, tickdir):
        """Set tick direction.  Valid values are 'out', 'in', 'inout'."""
        # This method is responsible for verifying input and, in subclasses, for setting
        # the tick{1,2}line markers.  From the user perspective this should always be
        # called through _apply_params, which further updates ticklabel positions using
        # the new pads.
        if tickdir is None:
            tickdir = mpl.rcParams[f'{self.__name__}.direction']
        else:
            _api.check_in_list(['in', 'out', 'inout'], tickdir=tickdir)
        self._tickdir = tickdir

    def get_tickdir(self):
        return self._tickdir

    def get_tick_padding(self):
        """Get the length of the tick outside of the Axes."""
        padding = {
            'in': 0.0,
            'inout': 0.5,
            'out': 1.0
        }
        return self._size * padding[self._tickdir]

    def get_children(self):
        children = [self.tick1line, self.tick2line,
                    self.gridline, self.label1, self.label2]
        return children

    def set_clip_path(self, path, transform=None):
        # docstring inherited
        super().set_clip_path(path, transform)
        self.gridline.set_clip_path(path, transform)
        self.stale = True

    def contains(self, mouseevent):
        """
        Test whether the mouse event occurred in the Tick marks.

        This function always returns false.  It is more useful to test if the
        axis as a whole contains the mouse rather than the set of tick marks.
        """
        return False, {}

    def set_pad(self, val):
        """
        Set the tick label pad in points

        Parameters
        ----------
        val : float
        """
        self._apply_params(pad=val)
        self.stale = True

    def get_pad(self):
        """Get the value of the tick label pad in points."""
        return self._base_pad

    def get_loc(self):
        """Return the tick location (data coords) as a scalar."""
        return self._loc

    @martist.allow_rasterization
    def draw(self, renderer):
        if not self.get_visible():
            self.stale = False
            return
        renderer.open_group(self.__name__, gid=self.get_gid())
        for artist in [self.gridline, self.tick1line, self.tick2line,
                       self.label1, self.label2]:
            artist.draw(renderer)
        renderer.close_group(self.__name__)
        self.stale = False

    def set_url(self, url):
        """
        Set the url of label1 and label2.

        Parameters
        ----------
        url : str
        """
        super().set_url(url)
        self.label1.set_url(url)
        self.label2.set_url(url)
        self.stale = True

    def _set_artist_props(self, a):
        a.set_figure(self.get_figure(root=False))

    def get_view_interval(self):
        """
        Return the view limits ``(min, max)`` of the axis the tick belongs to.
        """
        raise NotImplementedError('Derived must override')

    def _apply_params(self, **kwargs):
        for name, target in [("gridOn", self.gridline),
                             ("tick1On", self.tick1line),
                             ("tick2On", self.tick2line),
                             ("label1On", self.label1),
                             ("label2On", self.label2)]:
            if name in kwargs:
                target.set_visible(kwargs.pop(name))
        if any(k in kwargs for k in ['size', 'width', 'pad', 'tickdir']):
            self._size = kwargs.pop('size', self._size)
            # Width could be handled outside this block, but it is
            # convenient to leave it here.
            self._width = kwargs.pop('width', self._width)
            self._base_pad = kwargs.pop('pad', self._base_pad)
            # _apply_tickdir uses _size and _base_pad to make _pad, and also
            # sets the ticklines markers.
            self._apply_tickdir(kwargs.pop('tickdir', self._tickdir))
            for line in (self.tick1line, self.tick2line):
                line.set_markersize(self._size)
                line.set_markeredgewidth(self._width)
            # _get_text1_transform uses _pad from _apply_tickdir.
            trans = self._get_text1_transform()[0]
            self.label1.set_transform(trans)
            trans = self._get_text2_transform()[0]
            self.label2.set_transform(trans)
        tick_kw = {k: v for k, v in kwargs.items() if k in ['color', 'zorder']}
        if 'color' in kwargs:
            tick_kw['markeredgecolor'] = kwargs['color']
        self.tick1line.set(**tick_kw)
        self.tick2line.set(**tick_kw)
        for k, v in tick_kw.items():
            setattr(self, '_' + k, v)

        if 'labelrotation' in kwargs:
            self._set_labelrotation(kwargs.pop('labelrotation'))
            self.label1.set(rotation=self._labelrotation[1])
            self.label2.set(rotation=self._labelrotation[1])

        label_kw = {k[5:]: v for k, v in kwargs.items()
                    if k in ['labelsize', 'labelcolor', 'labelfontfamily']}
        self.label1.set(**label_kw)
        self.label2.set(**label_kw)

        grid_kw = {k[5:]: v for k, v in kwargs.items()
                   if k in _gridline_param_names}
        self.gridline.set(**grid_kw)

    def update_position(self, loc):
        """Set the location of tick in data coords with scalar *loc*."""
        raise NotImplementedError('Derived must override')

    def _get_text1_transform(self):
        raise NotImplementedError('Derived must override')

    def _get_text2_transform(self):
        raise NotImplementedError('Derived must override')


class XTick(Tick):
    """
    Contains all the Artists needed to make an x tick - the tick line,
    the label text and the grid line
    """
    __name__ = 'xtick'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # x in data coords, y in axes coords
        ax = self.axes
        self.tick1line.set(
            data=([0], [0]), transform=ax.get_xaxis_transform("tick1"))
        self.tick2line.set(
            data=([0], [1]), transform=ax.get_xaxis_transform("tick2"))
        self.gridline.set(
            data=([0, 0], [0, 1]), transform=ax.get_xaxis_transform("grid"))
        # the y loc is 3 points below the min of y axis
        trans, va, ha = self._get_text1_transform()
        self.label1.set(
            x=0, y=0,
            verticalalignment=va, horizontalalignment=ha, transform=trans,
        )
        trans, va, ha = self._get_text2_transform()
        self.label2.set(
            x=0, y=1,
            verticalalignment=va, horizontalalignment=ha, transform=trans,
        )

    def _get_text1_transform(self):
        return self.axes.get_xaxis_text1_transform(self._pad)

    def _get_text2_transform(self):
        return self.axes.get_xaxis_text2_transform(self._pad)

    def _apply_tickdir(self, tickdir):
        # docstring inherited
        super()._apply_tickdir(tickdir)
        mark1, mark2 = {
            'out': (mlines.TICKDOWN, mlines.TICKUP),
            'in': (mlines.TICKUP, mlines.TICKDOWN),
            'inout': ('|', '|'),
        }[self._tickdir]
        self.tick1line.set_marker(mark1)
        self.tick2line.set_marker(mark2)

    def update_position(self, loc):
        """Set the location of tick in data coords with scalar *loc*."""
        self.tick1line.set_xdata((loc,))
        self.tick2line.set_xdata((loc,))
        self.gridline.set_xdata((loc,))
        self.label1.set_x(loc)
        self.label2.set_x(loc)
        self._loc = loc
        self.stale = True

    def get_view_interval(self):
        # docstring inherited
        return self.axes.viewLim.intervalx


class YTick(Tick):
    """
    Contains all the Artists needed to make a Y tick - the tick line,
    the label text and the grid line
    """
    __name__ = 'ytick'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # x in axes coords, y in data coords
        ax = self.axes
        self.tick1line.set(
            data=([0], [0]), transform=ax.get_yaxis_transform("tick1"))
        self.tick2line.set(
            data=([1], [0]), transform=ax.get_yaxis_transform("tick2"))
        self.gridline.set(
            data=([0, 1], [0, 0]), transform=ax.get_yaxis_transform("grid"))
        # the y loc is 3 points below the min of y axis
        trans, va, ha = self._get_text1_transform()
        self.label1.set(
            x=0, y=0,
            verticalalignment=va, horizontalalignment=ha, transform=trans,
        )
        trans, va, ha = self._get_text2_transform()
        self.label2.set(
            x=1, y=0,
            verticalalignment=va, horizontalalignment=ha, transform=trans,
        )

    def _get_text1_transform(self):
        return self.axes.get_yaxis_text1_transform(self._pad)

    def _get_text2_transform(self):
        return self.axes.get_yaxis_text2_transform(self._pad)

    def _apply_tickdir(self, tickdir):
        # docstring inherited
        super()._apply_tickdir(tickdir)
        mark1, mark2 = {
            'out': (mlines.TICKLEFT, mlines.TICKRIGHT),
            'in': (mlines.TICKRIGHT, mlines.TICKLEFT),
            'inout': ('_', '_'),
        }[self._tickdir]
        self.tick1line.set_marker(mark1)
        self.tick2line.set_marker(mark2)

    def update_position(self, loc):
        """Set the location of tick in data coords with scalar *loc*."""
        self.tick1line.set_ydata((loc,))
        self.tick2line.set_ydata((loc,))
        self.gridline.set_ydata((loc,))
        self.label1.set_y(loc)
        self.label2.set_y(loc)
        self._loc = loc
        self.stale = True

    def get_view_interval(self):
        # docstring inherited
        return self.axes.viewLim.intervaly


class Ticker:
    """
    A container for the objects defining tick position and format.

    Attributes
    ----------
    locator : `~matplotlib.ticker.Locator` subclass
        Determines the positions of the ticks.
    formatter : `~matplotlib.ticker.Formatter` subclass
        Determines the format of the tick labels.
    """

    def __init__(self):
        self._locator = None
        self._formatter = None
        self._locator_is_default = True
        self._formatter_is_default = True

    @property
    def locator(self):
        return self._locator

    @locator.setter
    def locator(self, locator):
        if not isinstance(locator, mticker.Locator):
            raise TypeError('locator must be a subclass of '
                            'matplotlib.ticker.Locator')
        self._locator = locator

    @property
    def formatter(self):
        return self._formatter

    @formatter.setter
    def formatter(self, formatter):
        if not isinstance(formatter, mticker.Formatter):
            raise TypeError('formatter must be a subclass of '
                            'matplotlib.ticker.Formatter')
        self._formatter = formatter


class _LazyTickList:
    """
    A descriptor for lazy instantiation of tick lists.

    See comment above definition of the ``majorTicks`` and ``minorTicks``
    attributes.
    """

    def __init__(self, major):
        self._major = major

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            # instance._get_tick() can itself try to access the majorTicks
            # attribute (e.g. in certain projection classes which override
            # e.g. get_xaxis_text1_transform).  In order to avoid infinite
            # recursion, first set the majorTicks on the instance temporarily
            # to an empty lis. Then create the tick; note that _get_tick()
            # may call reset_ticks(). Therefore, the final tick list is
            # created and assigned afterwards.
            if self._major:
                instance.majorTicks = []
                tick = instance._get_tick(major=True)
                instance.majorTicks = [tick]
                return instance.majorTicks
            else:
                instance.minorTicks = []
                tick = instance._get_tick(major=False)
                instance.minorTicks = [tick]
                return instance.minorTicks


class Axis(martist.Artist):
    """
    Base class for `.XAxis` and `.YAxis`.

    Attributes
    ----------
    isDefault_label : bool

    axes : `~matplotlib.axes.Axes`
        The `~.axes.Axes` to which the Axis belongs.
    major : `~matplotlib.axis.Ticker`
        Determines the major tick positions and their label format.
    minor : `~matplotlib.axis.Ticker`
        Determines the minor tick positions and their label format.
    callbacks : `~matplotlib.cbook.CallbackRegistry`

    label : `~matplotlib.text.Text`
        The axis label.
    labelpad : float
        The distance between the axis label and the tick labels.
        Defaults to :rc:`axes.labelpad`.
    offsetText : `~matplotlib.text.Text`
        A `.Text` object containing the data offset of the ticks (if any).
    pickradius : float
        The acceptance radius for containment tests. See also `.Axis.contains`.
    majorTicks : list of `.Tick`
        The major ticks.

        .. warning::

            Ticks are not guaranteed to be persistent. Various operations
            can create, delete and modify the Tick instances. There is an
            imminent risk that changes to individual ticks will not
            survive if you work on the figure further (including also
            panning/zooming on a displayed figure).

            Working on the individual ticks is a method of last resort.
            Use `.set_tick_params` instead if possible.

    minorTicks : list of `.Tick`
        The minor ticks.
    """
    OFFSETTEXTPAD = 3
    # The class used in _get_tick() to create tick instances. Must either be
    # overwritten in subclasses, or subclasses must reimplement _get_tick().
    _tick_class = None
    converter = _api.deprecate_privatize_attribute(
                    "3.10",
                    alternative="get_converter and set_converter methods"
                )

    def __str__(self):
        return "{}({},{})".format(
            type(self).__name__, *self.axes.transAxes.transform((0, 0)))

    def __init__(self, axes, *, pickradius=15, clear=True):
        """
        Parameters
        ----------
        axes : `~matplotlib.axes.Axes`
            The `~.axes.Axes` to which the created Axis belongs.
        pickradius : float
            The acceptance radius for containment tests. See also
            `.Axis.contains`.
        clear : bool, default: True
            Whether to clear the Axis on creation. This is not required, e.g.,  when
            creating an Axis as part of an Axes, as ``Axes.clear`` will call
            ``Axis.clear``.
            .. versionadded:: 3.8
        """
        super().__init__()
        self._remove_overlapping_locs = True

        self.set_figure(axes.get_figure(root=False))

        self.isDefault_label = True

        self.axes = axes
        self.major = Ticker()
        self.minor = Ticker()
        self.callbacks = cbook.CallbackRegistry(signals=["units"])

        self._autolabelpos = True

        self.label = mtext.Text(
            np.nan, np.nan,
            fontsize=mpl.rcParams['axes.labelsize'],
            fontweight=mpl.rcParams['axes.labelweight'],
            color=mpl.rcParams['axes.labelcolor'],
        )  #: The `.Text` object of the axis label.

        self._set_artist_props(self.label)
        self.offsetText = mtext.Text(np.nan, np.nan)
        self._set_artist_props(self.offsetText)

        self.labelpad = mpl.rcParams['axes.labelpad']

        self.pickradius = pickradius

        # Initialize here for testing; later add API
        self._major_tick_kw = dict()
        self._minor_tick_kw = dict()

        if clear:
            self.clear()
        else:
            self._converter = None
            self._converter_is_explicit = False
            self.units = None

        self._autoscale_on = True

    @property
    def isDefault_majloc(self):
        return self.major._locator_is_default

    @isDefault_majloc.setter
    def isDefault_majloc(self, value):
        self.major._locator_is_default = value

    @property
    def isDefault_majfmt(self):
        return self.major._formatter_is_default

    @isDefault_majfmt.setter
    def isDefault_majfmt(self, value):
        self.major._formatter_is_default = value

    @property
    def isDefault_minloc(self):
        return self.minor._locator_is_default

    @isDefault_minloc.setter
    def isDefault_minloc(self, value):
        self.minor._locator_is_default = value

    @property
    def isDefault_minfmt(self):
        return self.minor._formatter_is_default

    @isDefault_minfmt.setter
    def isDefault_minfmt(self, value):
        self.minor._formatter_is_default = value

    def _get_shared_axes(self):
        """Return Grouper of shared Axes for current axis."""
        return self.axes._shared_axes[
            self._get_axis_name()].get_siblings(self.axes)

    def _get_shared_axis(self):
        """Return list of shared axis for current axis."""
        name = self._get_axis_name()
        return [ax._axis_map[name] for ax in self._get_shared_axes()]

    def _get_axis_name(self):
        """Return the axis name."""
        return next(name for name, axis in self.axes._axis_map.items()
                    if axis is self)

    # During initialization, Axis objects often create ticks that are later
    # unused; this turns out to be a very slow step.  Instead, use a custom
    # descriptor to make the tick lists lazy and instantiate them as needed.
    majorTicks = _LazyTickList(major=True)
    minorTicks = _LazyTickList(major=False)

    def get_remove_overlapping_locs(self):
        return self._remove_overlapping_locs

    def set_remove_overlapping_locs(self, val):
        self._remove_overlapping_locs = bool(val)

    remove_overlapping_locs = property(
        get_remove_overlapping_locs, set_remove_overlapping_locs,
        doc=('If minor ticker locations that overlap with major '
             'ticker locations should be trimmed.'))

    def set_label_coords(self, x, y, transform=None):
        """
        Set the coordinates of the label.

        By default, the x coordinate of the y label and the y coordinate of the
        x label are determined by the tick label bounding boxes, but this can
        lead to poor alignment of multiple labels if there are multiple Axes.

        You can also specify the coordinate system of the label with the
        transform.  If None, the default coordinate system will be the axes
        coordinate system: (0, 0) is bottom left, (0.5, 0.5) is center, etc.
        """
        self._autolabelpos = False
        if transform is None:
            transform = self.axes.transAxes

        self.label.set_transform(transform)
        self.label.set_position((x, y))
        self.stale = True

    def get_transform(self):
        """Return the transform used in the Axis' scale"""
        return self._scale.get_transform()

    def get_scale(self):
        """Return this Axis' scale (as a str)."""
        return self._scale.name

    def _set_scale(self, value, **kwargs):
        if not isinstance(value, mscale.ScaleBase):
            self._scale = mscale.scale_factory(value, self, **kwargs)
        else:
            self._scale = value
        self._scale.set_default_locators_and_formatters(self)

        self.isDefault_majloc = True
        self.isDefault_minloc = True
        self.isDefault_majfmt = True
        self.isDefault_minfmt = True

    # This method is directly wrapped by Axes.set_{x,y}scale.
    def _set_axes_scale(self, value, **kwargs):
        """
        Set this Axis' scale.

        Parameters
        ----------
        value : str or `.ScaleBase`
            The axis scale type to apply.  Valid string values are the names of scale
            classes ("linear", "log", "function",...).  These may be the names of any
            of the :ref:`built-in scales<builtin_scales>` or of any custom scales
            registered using `matplotlib.scale.register_scale`.

        **kwargs
            If *value* is a string, keywords are passed to the instantiation method of
            the respective class.
        """
        name = self._get_axis_name()
        old_default_lims = (self.get_major_locator()
                            .nonsingular(-np.inf, np.inf))
        for ax in self._get_shared_axes():
            ax._axis_map[name]._set_scale(value, **kwargs)
            ax._update_transScale()
            ax.stale = True
        new_default_lims = (self.get_major_locator()
                            .nonsingular(-np.inf, np.inf))
        if old_default_lims != new_default_lims:
            # Force autoscaling now, to take advantage of the scale locator's
            # nonsingular() before it possibly gets swapped out by the user.
            self.axes.autoscale_view(
                **{f"scale{k}": k == name for k in self.axes._axis_names})

    def limit_range_for_scale(self, vmin, vmax):
        """
        Return the range *vmin*, *vmax*, restricted to the domain supported by the
        current scale.
        """
        return self._scale.limit_range_for_scale(vmin, vmax, self.get_minpos())

    def _get_autoscale_on(self):
        """Return whether this Axis is autoscaled."""
        return self._autoscale_on

    def _set_autoscale_on(self, b):
        """
        Set whether this Axis is autoscaled when drawing or by `.Axes.autoscale_view`.

        If b is None, then the value is not changed.

        Parameters
        ----------
        b : bool
        """
        if b is not None:
            self._autoscale_on = b

    def get_children(self):
        return [self.label, self.offsetText,
                *self.get_major_ticks(), *self.get_minor_ticks()]

    def _reset_major_tick_kw(self):
        self._major_tick_kw.clear()
        self._major_tick_kw['gridOn'] = (
                mpl.rcParams['axes.grid'] and
                mpl.rcParams['axes.grid.which'] in ('both', 'major'))

    def _reset_minor_tick_kw(self):
        self._minor_tick_kw.clear()
        self._minor_tick_kw['gridOn'] = (
                mpl.rcParams['axes.grid'] and
                mpl.rcParams['axes.grid.which'] in ('both', 'minor'))

    def clear(self):
        """
        Clear the axis.

        This resets axis properties to their default values:

        - the label
        - the scale
        - locators, formatters and ticks
        - major and minor grid
        - units
        - registered callbacks
        """
        self.label._reset_visual_defaults()
        # The above resets the label formatting using text rcParams,
        # so we then update the formatting using axes rcParams
        self.label.set_color(mpl.rcParams['axes.labelcolor'])
        self.label.set_fontsize(mpl.rcParams['axes.labelsize'])
        self.label.set_fontweight(mpl.rcParams['axes.labelweight'])
        self.offsetText._reset_visual_defaults()
        self.labelpad = mpl.rcParams['axes.labelpad']

        self._init()

        self._set_scale('linear')

        # Clear the callback registry for this axis, or it may "leak"
        self.callbacks = cbook.CallbackRegistry(signals=["units"])

        # whether the grids are on
        self._major_tick_kw['gridOn'] = (
                mpl.rcParams['axes.grid'] and
                mpl.rcParams['axes.grid.which'] in ('both', 'major'))
        self._minor_tick_kw['gridOn'] = (
                mpl.rcParams['axes.grid'] and
                mpl.rcParams['axes.grid.which'] in ('both', 'minor'))
        self.reset_ticks()

        self._converter = None
        self._converter_is_explicit = False
        self.units = None
        self.stale = True

    def reset_ticks(self):
        """
        Re-initialize the major and minor Tick lists.

        Each list starts with a single fresh Tick.
        """
        # Restore the lazy tick lists.
        try:
            del self.majorTicks
        except AttributeError:
            pass
        try:
            del self.minorTicks
        except AttributeError:
            pass
        try:
            self.set_clip_path(self.axes.patch)
        except AttributeError:
            pass

    def minorticks_on(self):
        """
        Display default minor ticks on the Axis, depending on the scale
        (`~.axis.Axis.get_scale`).

        Scales use specific minor locators:

        - log: `~.LogLocator`
        - symlog: `~.SymmetricalLogLocator`
        - asinh: `~.AsinhLocator`
        - logit: `~.LogitLocator`
        - default: `~.AutoMinorLocator`

        Displaying minor ticks may reduce performance; you may turn them off
        using `minorticks_off()` if drawing speed is a problem.
        """
        scale = self.get_scale()
        if scale == 'log':
            s = self._scale
            self.set_minor_locator(mticker.LogLocator(s.base, s.subs))
        elif scale == 'symlog':
            s = self._scale
            self.set_minor_locator(
                mticker.SymmetricalLogLocator(s._transform, s.subs))
        elif scale == 'asinh':
            s = self._scale
            self.set_minor_locator(
                    mticker.AsinhLocator(s.linear_width, base=s._base,
                                         subs=s._subs))
        elif scale == 'logit':
            self.set_minor_locator(mticker.LogitLocator(minor=True))
        else:
            self.set_minor_locator(mticker.AutoMinorLocator())

    def minorticks_off(self):
        """Remove minor ticks from the Axis."""
        self.set_minor_locator(mticker.NullLocator())

    def set_tick_params(self, which='major', reset=False, **kwargs):
        """
        Set appearance parameters for ticks, ticklabels, and gridlines.

        For documentation of keyword arguments, see
        :meth:`matplotlib.axes.Axes.tick_params`.

        See Also
        --------
        .Axis.get_tick_params
            View the current style settings for ticks, ticklabels, and
            gridlines.
        """
        _api.check_in_list(['major', 'minor', 'both'], which=which)
        kwtrans = self._translate_tick_params(kwargs)

        # the kwargs are stored in self._major/minor_tick_kw so that any
        # future new ticks will automatically get them
        if reset:
            if which in ['major', 'both']:
                self._reset_major_tick_kw()
                self._major_tick_kw.update(kwtrans)
            if which in ['minor', 'both']:
                self._reset_minor_tick_kw()
                self._minor_tick_kw.update(kwtrans)
            self.reset_ticks()
        else:
            if which in ['major', 'both']:
                self._major_tick_kw.update(kwtrans)
                for tick in self.majorTicks:
                    tick._apply_params(**kwtrans)
            if which in ['minor', 'both']:
                self._minor_tick_kw.update(kwtrans)
                for tick in self.minorTicks:
                    tick._apply_params(**kwtrans)
            # labelOn and labelcolor also apply to the offset text.
            if 'label1On' in kwtrans or 'label2On' in kwtrans:
                self.offsetText.set_visible(
                    self._major_tick_kw.get('label1On', False)
                    or self._major_tick_kw.get('label2On', False))
            if 'labelcolor' in kwtrans:
                self.offsetText.set_color(kwtrans['labelcolor'])

        self.stale = True

    def get_tick_params(self, which='major'):
        """
        Get appearance parameters for ticks, ticklabels, and gridlines.

        .. versionadded:: 3.7

        Parameters
        ----------
        which : {'major', 'minor'}, default: 'major'
            The group of ticks for which the parameters are retrieved.

        Returns
        -------
        dict
            Properties for styling tick elements added to the axis.

        Notes
        -----
        This method returns the appearance parameters for styling *new*
        elements added to this axis and may be different from the values
        on current elements if they were modified directly by the user
        (e.g., via ``set_*`` methods on individual tick objects).

        Examples
        --------
        ::

            >>> ax.yaxis.set_tick_params(labelsize=30, labelcolor='red',
            ...                          direction='out', which='major')
            >>> ax.yaxis.get_tick_params(which='major')
            {'direction': 'out',
            'left': True,
            'right': False,
            'labelleft': True,
            'labelright': False,
            'gridOn': False,
            'labelsize': 30,
            'labelcolor': 'red'}
            >>> ax.yaxis.get_tick_params(which='minor')
            {'left': True,
            'right': False,
            'labelleft': True,
            'labelright': False,
            'gridOn': False}


        """
        _api.check_in_list(['major', 'minor'], which=which)
        if which == 'major':
            return self._translate_tick_params(
                self._major_tick_kw, reverse=True
            )
        return self._translate_tick_params(self._minor_tick_kw, reverse=True)

    @classmethod
    def _translate_tick_params(cls, kw, reverse=False):
        """
        Translate the kwargs supported by `.Axis.set_tick_params` to kwargs
        supported by `.Tick._apply_params`.

        In particular, this maps axis specific names like 'top', 'left'
        to the generic tick1, tick2 logic of the axis. Additionally, there
        are some other name translations.

        Returns a new dict of translated kwargs.

        Note: Use reverse=True to translate from those supported by
        `.Tick._apply_params` back to those supported by
        `.Axis.set_tick_params`.
        """
        kw_ = {**kw}

        # The following lists may be moved to a more accessible location.
        allowed_keys = [
            'size', 'width', 'color', 'tickdir', 'pad',
            'labelsize', 'labelcolor', 'labelfontfamily', 'zorder', 'gridOn',
            'tick1On', 'tick2On', 'label1On', 'label2On',
            'length', 'direction', 'left', 'bottom', 'right', 'top',
            'labelleft', 'labelbottom', 'labelright', 'labeltop',
            'labelrotation',
            *_gridline_param_names]

        keymap = {
            # tick_params key -> axis key
            'length': 'size',
            'direction': 'tickdir',
            'rotation': 'labelrotation',
            'left': 'tick1On',
            'bottom': 'tick1On',
            'right': 'tick2On',
            'top': 'tick2On',
            'labelleft': 'label1On',
            'labelbottom': 'label1On',
            'labelright': 'label2On',
            'labeltop': 'label2On',
        }
        if reverse:
            kwtrans = {}
            is_x_axis = cls.axis_name == 'x'
            y_axis_keys = ['left', 'right', 'labelleft', 'labelright']
            for oldkey, newkey in keymap.items():
                if newkey in kw_:
                    if is_x_axis and oldkey in y_axis_keys:
                        continue
                    else:
                        kwtrans[oldkey] = kw_.pop(newkey)
        else:
            kwtrans = {
                newkey: kw_.pop(oldkey)
                for oldkey, newkey in keymap.items() if oldkey in kw_
            }
        if 'colors' in kw_:
            c = kw_.pop('colors')
            kwtrans['color'] = c
            kwtrans['labelcolor'] = c
        # Maybe move the checking up to the caller of this method.
        for key in kw_:
            if key not in allowed_keys:
                raise ValueError(
                    "keyword %s is not recognized; valid keywords are %s"
                    % (key, allowed_keys))
        kwtrans.update(kw_)
        return kwtrans

    def set_clip_path(self, path, transform=None):
        super().set_clip_path(path, transform)
        for child in self.majorTicks + self.minorTicks:
            child.set_clip_path(path, transform)
        self.stale = True

    def get_view_interval(self):
        """Return the ``(min, max)`` view limits of this axis."""
        raise NotImplementedError('Derived must override')

    def set_view_interval(self, vmin, vmax, ignore=False):
        """
        Set the axis view limits.  This method is for internal use; Matplotlib
        users should typically use e.g. `~.Axes.set_xlim` or `~.Axes.set_ylim`.

        If *ignore* is False (the default), this method will never reduce the
        preexisting view limits, only expand them if *vmin* or *vmax* are not
        within them.  Moreover, the order of *vmin* and *vmax* does not matter;
        the orientation of the axis will not change.

        If *ignore* is True, the view limits will be set exactly to ``(vmin,
        vmax)`` in that order.
        """
        raise NotImplementedError('Derived must override')

    def get_data_interval(self):
        """Return the ``(min, max)`` data limits of this axis."""
        raise NotImplementedError('Derived must override')

    def set_data_interval(self, vmin, vmax, ignore=False):
        """
        Set the axis data limits.  This method is for internal use.

        If *ignore* is False (the default), this method will never reduce the
        preexisting data limits, only expand them if *vmin* or *vmax* are not
        within them.  Moreover, the order of *vmin* and *vmax* does not matter;
        the orientation of the axis will not change.

        If *ignore* is True, the data limits will be set exactly to ``(vmin,
        vmax)`` in that order.
        """
        raise NotImplementedError('Derived must override')

    def get_inverted(self):
        """
        Return whether this Axis is oriented in the "inverse" direction.

        The "normal" direction is increasing to the right for the x-axis and to
        the top for the y-axis; the "inverse" direction is increasing to the
        left for the x-axis and to the bottom for the y-axis.
        """
        low, high = self.get_view_interval()
        return high < low

    def set_inverted(self, inverted):
        """
        Set whether this Axis is oriented in the "inverse" direction.

        The "normal" direction is increasing to the right for the x-axis and to
        the top for the y-axis; the "inverse" direction is increasing to the
        left for the x-axis and to the bottom for the y-axis.
        """
        a, b = self.get_view_interval()
        # cast to bool to avoid bad interaction between python 3.8 and np.bool_
        self._set_lim(*sorted((a, b), reverse=bool(inverted)), auto=None)

    def set_default_intervals(self):
        """
        Set the default limits for the axis data and view interval if they
        have not been not mutated yet.
        """
        # this is mainly in support of custom object plotting.  For
        # example, if someone passes in a datetime object, we do not
        # know automagically how to set the default min/max of the
        # data and view limits.  The unit conversion AxisInfo
        # interface provides a hook for custom types to register
        # default limits through the AxisInfo.default_limits
        # attribute, and the derived code below will check for that
        # and use it if it's available (else just use 0..1)

    def _set_lim(self, v0, v1, *, emit=True, auto):
        """
        Set view limits.

        This method is a helper for the Axes ``set_xlim``, ``set_ylim``, and
        ``set_zlim`` methods.

        Parameters
        ----------
        v0, v1 : float
            The view limits.  (Passing *v0* as a (low, high) pair is not
            supported; normalization must occur in the Axes setters.)
        emit : bool, default: True
            Whether to notify observers of limit change.
        auto : bool or None, default: False
            Whether to turn on autoscaling of the x-axis. True turns on, False
            turns off, None leaves unchanged.
        """
        name = self._get_axis_name()

        self.axes._process_unit_info([(name, (v0, v1))], convert=False)
        v0 = self.axes._validate_converted_limits(v0, self.convert_units)
        v1 = self.axes._validate_converted_limits(v1, self.convert_units)

        if v0 is None or v1 is None:
            # Axes init calls set_xlim(0, 1) before get_xlim() can be called,
            # so only grab the limits if we really need them.
            old0, old1 = self.get_view_interval()
            if v0 is None:
                v0 = old0
            if v1 is None:
                v1 = old1

        if self.get_scale() == 'log' and (v0 <= 0 or v1 <= 0):
            # Axes init calls set_xlim(0, 1) before get_xlim() can be called,
            # so only grab the limits if we really need them.
            old0, old1 = self.get_view_interval()
            if v0 <= 0:
                _api.warn_external(f"Attempt to set non-positive {name}lim on "
                                   f"a log-scaled axis will be ignored.")
                v0 = old0
            if v1 <= 0:
                _api.warn_external(f"Attempt to set non-positive {name}lim on "
                                   f"a log-scaled axis will be ignored.")
                v1 = old1
        if v0 == v1:
            _api.warn_external(
                f"Attempting to set identical low and high {name}lims "
                f"makes transformation singular; automatically expanding.")
        reverse = bool(v0 > v1)  # explicit cast needed for python3.8+np.bool_.
        v0, v1 = self.get_major_locator().nonsingular(v0, v1)
        v0, v1 = self.limit_range_for_scale(v0, v1)
        v0, v1 = sorted([v0, v1], reverse=bool(reverse))

        self.set_view_interval(v0, v1, ignore=True)
        # Mark viewlims as no longer stale without triggering an autoscale.
        for ax in self._get_shared_axes():
            ax._stale_viewlims[name] = False
        self._set_autoscale_on(auto)

        if emit:
            self.axes.callbacks.process(f"{name}lim_changed", self.axes)
            # Call all of the other Axes that are shared with this one
            for other in self._get_shared_axes():
                if other is self.axes:
                    continue
                other._axis_map[name]._set_lim(v0, v1, emit=False, auto=auto)
                if emit:
                    other.callbacks.process(f"{name}lim_changed", other)
                if ((other_fig := other.get_figure(root=False)) !=
                        self.get_figure(root=False)):
                    other_fig.canvas.draw_idle()

        self.stale = True
        return v0, v1

    def _set_artist_props(self, a):
        if a is None:
            return
        a.set_figure(self.get_figure(root=False))

    def _update_ticks(self):
        """
        Update ticks (position and labels) using the current data interval of
        the axes.  Return the list of ticks that will be drawn.
        """
        major_locs = self.get_majorticklocs()
        major_labels = self.major.formatter.format_ticks(major_locs)
        major_ticks = self.get_major_ticks(len(major_locs))
        for tick, loc, label in zip(major_ticks, major_locs, major_labels):
            tick.update_position(loc)
            tick.label1.set_text(label)
            tick.label2.set_text(label)
        minor_locs = self.get_minorticklocs()
        minor_labels = self.minor.formatter.format_ticks(minor_locs)
        minor_ticks = self.get_minor_ticks(len(minor_locs))
        for tick, loc, label in zip(minor_ticks, minor_locs, minor_labels):
            tick.update_position(loc)
            tick.label1.set_text(label)
            tick.label2.set_text(label)
        ticks = [*major_ticks, *minor_ticks]

        view_low, view_high = self.get_view_interval()
        if view_low > view_high:
            view_low, view_high = view_high, view_low

        if (hasattr(self, "axes") and self.axes.name == '3d'
                and mpl.rcParams['axes3d.automargin']):
            # In mpl3.8, the margin was 1/48. Due to the change in automargin
            # behavior in mpl3.9, we need to adjust this to compensate for a
            # zoom factor of 2/48, giving us a 23/24 modifier. So the new
            # margin is 0.019965277777777776 = 1/48*23/24.
            margin = 0.019965277777777776
            delta = view_high - view_low
            view_high = view_high - delta * margin
            view_low = view_low + delta * margin

        interval_t = self.get_transform().transform([view_low, view_high])

        ticks_to_draw = []
        for tick in ticks:
            try:
                loc_t = self.get_transform().transform(tick.get_loc())
            except AssertionError:
                # transforms.transform doesn't allow masked values but
                # some scales might make them, so we need this try/except.
                pass
            else:
                if mtransforms._interval_contains_close(interval_t, loc_t):
                    ticks_to_draw.append(tick)

        return ticks_to_draw

    def _get_ticklabel_bboxes(self, ticks, renderer=None):
        """Return lists of bboxes for ticks' label1's and label2's."""
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        return ([tick.label1.get_window_extent(renderer)
                 for tick in ticks if tick.label1.get_visible()],
                [tick.label2.get_window_extent(renderer)
                 for tick in ticks if tick.label2.get_visible()])

    def get_tightbbox(self, renderer=None, *, for_layout_only=False):
        """
        Return a bounding box that encloses the axis. It only accounts
        tick labels, axis label, and offsetText.

        If *for_layout_only* is True, then the width of the label (if this
        is an x-axis) or the height of the label (if this is a y-axis) is
        collapsed to near zero.  This allows tight/constrained_layout to ignore
        too-long labels when doing their layout.
        """
        if not self.get_visible() or for_layout_only and not self.get_in_layout():
            return
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        ticks_to_draw = self._update_ticks()

        self._update_label_position(renderer)

        # go back to just this axis's tick labels
        tlb1, tlb2 = self._get_ticklabel_bboxes(ticks_to_draw, renderer)

        self._update_offset_text_position(tlb1, tlb2)
        self.offsetText.set_text(self.major.formatter.get_offset())

        bboxes = [
            *(a.get_window_extent(renderer)
              for a in [self.offsetText]
              if a.get_visible()),
            *tlb1, *tlb2,
        ]
        # take care of label
        if self.label.get_visible():
            bb = self.label.get_window_extent(renderer)
            # for constrained/tight_layout, we want to ignore the label's
            # width/height because the adjustments they make can't be improved.
            # this code collapses the relevant direction
            if for_layout_only:
                if self.axis_name == "x" and bb.width > 0:
                    bb.x0 = (bb.x0 + bb.x1) / 2 - 0.5
                    bb.x1 = bb.x0 + 1.0
                if self.axis_name == "y" and bb.height > 0:
                    bb.y0 = (bb.y0 + bb.y1) / 2 - 0.5
                    bb.y1 = bb.y0 + 1.0
            bboxes.append(bb)
        bboxes = [b for b in bboxes
                  if 0 < b.width < np.inf and 0 < b.height < np.inf]
        if bboxes:
            return mtransforms.Bbox.union(bboxes)
        else:
            return None

    def get_tick_padding(self):
        values = []
        if len(self.majorTicks):
            values.append(self.majorTicks[0].get_tick_padding())
        if len(self.minorTicks):
            values.append(self.minorTicks[0].get_tick_padding())
        return max(values, default=0)

    @martist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited

        if not self.get_visible():
            return
        renderer.open_group(__name__, gid=self.get_gid())

        ticks_to_draw = self._update_ticks()
        tlb1, tlb2 = self._get_ticklabel_bboxes(ticks_to_draw, renderer)

        for tick in ticks_to_draw:
            tick.draw(renderer)

        # Shift label away from axes to avoid overlapping ticklabels.
        self._update_label_position(renderer)
        self.label.draw(renderer)

        self._update_offset_text_position(tlb1, tlb2)
        self.offsetText.set_text(self.major.formatter.get_offset())
        self.offsetText.draw(renderer)

        renderer.close_group(__name__)
        self.stale = False

    def get_gridlines(self):
        r"""Return this Axis' grid lines as a list of `.Line2D`\s."""
        ticks = self.get_major_ticks()
        return cbook.silent_list('Line2D gridline',
                                 [tick.gridline for tick in ticks])

    def set_label(self, s):
        """Assigning legend labels is not supported. Raises RuntimeError."""
        raise RuntimeError(
            "A legend label cannot be assigned to an Axis. Did you mean to "
            "set the axis label via set_label_text()?")

    def get_label(self):
        """
        Return the axis label as a Text instance.

        .. admonition:: Discouraged

           This overrides `.Artist.get_label`, which is for legend labels, with a new
           semantic. It is recommended to use the attribute ``Axis.label`` instead.
        """
        return self.label

    def get_offset_text(self):
        """Return the axis offsetText as a Text instance."""
        return self.offsetText

    def get_pickradius(self):
        """Return the depth of the axis used by the picker."""
        return self._pickradius

    def get_majorticklabels(self):
        """Return this Axis' major tick labels, as a list of `~.text.Text`."""
        self._update_ticks()
        ticks = self.get_major_ticks()
        labels1 = [tick.label1 for tick in ticks if tick.label1.get_visible()]
        labels2 = [tick.label2 for tick in ticks if tick.label2.get_visible()]
        return labels1 + labels2

    def get_minorticklabels(self):
        """Return this Axis' minor tick labels, as a list of `~.text.Text`."""
        self._update_ticks()
        ticks = self.get_minor_ticks()
        labels1 = [tick.label1 for tick in ticks if tick.label1.get_visible()]
        labels2 = [tick.label2 for tick in ticks if tick.label2.get_visible()]
        return labels1 + labels2

    def get_ticklabels(self, minor=False, which=None):
        """
        Get this Axis' tick labels.

        Parameters
        ----------
        minor : bool
           Whether to return the minor or the major ticklabels.

        which : None, ('minor', 'major', 'both')
           Overrides *minor*.

           Selects which ticklabels to return

        Returns
        -------
        list of `~matplotlib.text.Text`
        """
        if which is not None:
            if which == 'minor':
                return self.get_minorticklabels()
            elif which == 'major':
                return self.get_majorticklabels()
            elif which == 'both':
                return self.get_majorticklabels() + self.get_minorticklabels()
            else:
                _api.check_in_list(['major', 'minor', 'both'], which=which)
        if minor:
            return self.get_minorticklabels()
        return self.get_majorticklabels()

    def get_majorticklines(self):
        r"""Return this Axis' major tick lines as a list of `.Line2D`\s."""
        lines = []
        ticks = self.get_major_ticks()
        for tick in ticks:
            lines.append(tick.tick1line)
            lines.append(tick.tick2line)
        return cbook.silent_list('Line2D ticklines', lines)

    def get_minorticklines(self):
        r"""Return this Axis' minor tick lines as a list of `.Line2D`\s."""
        lines = []
        ticks = self.get_minor_ticks()
        for tick in ticks:
            lines.append(tick.tick1line)
            lines.append(tick.tick2line)
        return cbook.silent_list('Line2D ticklines', lines)

    def get_ticklines(self, minor=False):
        r"""Return this Axis' tick lines as a list of `.Line2D`\s."""
        if minor:
            return self.get_minorticklines()
        return self.get_majorticklines()

    def get_majorticklocs(self):
        """Return this Axis' major tick locations in data coordinates."""
        return self.major.locator()

    def get_minorticklocs(self):
        """Return this Axis' minor tick locations in data coordinates."""
        # Remove minor ticks duplicating major ticks.
        minor_locs = np.asarray(self.minor.locator())
        if self.remove_overlapping_locs:
            major_locs = self.major.locator()
            transform = self._scale.get_transform()
            tr_minor_locs = transform.transform(minor_locs)
            tr_major_locs = transform.transform(major_locs)
            lo, hi = sorted(transform.transform(self.get_view_interval()))
            # Use the transformed view limits as scale.  1e-5 is the default
            # rtol for np.isclose.
            tol = (hi - lo) * 1e-5
            mask = np.isclose(tr_minor_locs[:, None], tr_major_locs[None, :],
                              atol=tol, rtol=0).any(axis=1)
            minor_locs = minor_locs[~mask]
        return minor_locs

    def get_ticklocs(self, *, minor=False):
        """
        Return this Axis' tick locations in data coordinates.

        The locations are not clipped to the current axis limits and hence
        may contain locations that are not visible in the output.

        Parameters
        ----------
        minor : bool, default: False
            True to return the minor tick directions,
            False to return the major tick directions.

        Returns
        -------
        array of tick locations
        """
        return self.get_minorticklocs() if minor else self.get_majorticklocs()

    def get_ticks_direction(self, minor=False):
        """
        Return an array of this Axis' tick directions.

        Parameters
        ----------
        minor : bool, default: False
            True to return the minor tick directions,
            False to return the major tick directions.

        Returns
        -------
        array of tick directions
        """
        if minor:
            return np.array(
                [tick._tickdir for tick in self.get_minor_ticks()])
        else:
            return np.array(
                [tick._tickdir for tick in self.get_major_ticks()])

    def _get_tick(self, major):
        """Return the default tick instance."""
        if self._tick_class is None:
            raise NotImplementedError(
                f"The Axis subclass {self.__class__.__name__} must define "
                "_tick_class or reimplement _get_tick()")
        tick_kw = self._major_tick_kw if major else self._minor_tick_kw
        return self._tick_class(self.axes, 0, major=major, **tick_kw)

    def _get_tick_label_size(self, axis_name):
        """
        Return the text size of tick labels for this Axis.

        This is a convenience function to avoid having to create a `Tick` in
        `.get_tick_space`, since it is expensive.
        """
        tick_kw = self._major_tick_kw
        size = tick_kw.get('labelsize',
                           mpl.rcParams[f'{axis_name}tick.labelsize'])
        return mtext.FontProperties(size=size).get_size_in_points()

    def _copy_tick_props(self, src, dest):
        """Copy the properties from *src* tick to *dest* tick."""
        if src is None or dest is None:
            return
        dest.label1.update_from(src.label1)
        dest.label2.update_from(src.label2)
        dest.tick1line.update_from(src.tick1line)
        dest.tick2line.update_from(src.tick2line)
        dest.gridline.update_from(src.gridline)
        dest.update_from(src)
        dest._loc = src._loc
        dest._size = src._size
        dest._width = src._width
        dest._base_pad = src._base_pad
        dest._labelrotation = src._labelrotation
        dest._zorder = src._zorder
        dest._tickdir = src._tickdir

    def get_label_text(self):
        """Get the text of the label."""
        return self.label.get_text()

    def get_major_locator(self):
        """Get the locator of the major ticker."""
        return self.major.locator

    def get_minor_locator(self):
        """Get the locator of the minor ticker."""
        return self.minor.locator

    def get_major_formatter(self):
        """Get the formatter of the major ticker."""
        return self.major.formatter

    def get_minor_formatter(self):
        """Get the formatter of the minor ticker."""
        return self.minor.formatter

    def get_major_ticks(self, numticks=None):
        r"""
        Return the list of major `.Tick`\s.

        .. warning::

            Ticks are not guaranteed to be persistent. Various operations
            can create, delete and modify the Tick instances. There is an
            imminent risk that changes to individual ticks will not
            survive if you work on the figure further (including also
            panning/zooming on a displayed figure).

            Working on the individual ticks is a method of last resort.
            Use `.set_tick_params` instead if possible.
        """
        if numticks is None:
            numticks = len(self.get_majorticklocs())

        while len(self.majorTicks) < numticks:
            # Update the new tick label properties from the old.
            tick = self._get_tick(major=True)
            self.majorTicks.append(tick)
            self._copy_tick_props(self.majorTicks[0], tick)

        return self.majorTicks[:numticks]

    def get_minor_ticks(self, numticks=None):
        r"""
        Return the list of minor `.Tick`\s.

        .. warning::

            Ticks are not guaranteed to be persistent. Various operations
            can create, delete and modify the Tick instances. There is an
            imminent risk that changes to individual ticks will not
            survive if you work on the figure further (including also
            panning/zooming on a displayed figure).

            Working on the individual ticks is a method of last resort.
            Use `.set_tick_params` instead if possible.
        """
        if numticks is None:
            numticks = len(self.get_minorticklocs())

        while len(self.minorTicks) < numticks:
            # Update the new tick label properties from the old.
            tick = self._get_tick(major=False)
            self.minorTicks.append(tick)
            self._copy_tick_props(self.minorTicks[0], tick)

        return self.minorTicks[:numticks]

    def grid(self, visible=None, which='major', **kwargs):
        """
        Configure the grid lines.

        Parameters
        ----------
        visible : bool or None
            Whether to show the grid lines.  If any *kwargs* are supplied, it
            is assumed you want the grid on and *visible* will be set to True.

            If *visible* is *None* and there are no *kwargs*, this toggles the
            visibility of the lines.

        which : {'major', 'minor', 'both'}
            The grid lines to apply the changes on.

        **kwargs : `~matplotlib.lines.Line2D` properties
            Define the line properties of the grid, e.g.::

                grid(color='r', linestyle='-', linewidth=2)
        """
        if kwargs:
            if visible is None:
                visible = True
            elif not visible:  # something false-like but not None
                _api.warn_external('First parameter to grid() is false, '
                                   'but line properties are supplied. The '
                                   'grid will be enabled.')
                visible = True
        which = which.lower()
        _api.check_in_list(['major', 'minor', 'both'], which=which)
        gridkw = {f'grid_{name}': value for name, value in kwargs.items()}
        if which in ['minor', 'both']:
            gridkw['gridOn'] = (not self._minor_tick_kw['gridOn']
                                if visible is None else visible)
            self.set_tick_params(which='minor', **gridkw)
        if which in ['major', 'both']:
            gridkw['gridOn'] = (not self._major_tick_kw['gridOn']
                                if visible is None else visible)
            self.set_tick_params(which='major', **gridkw)
        self.stale = True

    def update_units(self, data):
        """
        Introspect *data* for units converter and update the
        ``axis.get_converter`` instance if necessary. Return *True*
        if *data* is registered for unit conversion.
        """
        if not self._converter_is_explicit:
            converter = munits.registry.get_converter(data)
        else:
            converter = self._converter

        if converter is None:
            return False

        neednew = self._converter != converter
        self._set_converter(converter)
        default = self._converter.default_units(data, self)
        if default is not None and self.units is None:
            self.set_units(default)

        elif neednew:
            self._update_axisinfo()
        self.stale = True
        return True

    def _update_axisinfo(self):
        """
        Check the axis converter for the stored units to see if the
        axis info needs to be updated.
        """
        if self._converter is None:
            return

        info = self._converter.axisinfo(self.units, self)

        if info is None:
            return
        if info.majloc is not None and \
           self.major.locator != info.majloc and self.isDefault_majloc:
            self.set_major_locator(info.majloc)
            self.isDefault_majloc = True
        if info.minloc is not None and \
           self.minor.locator != info.minloc and self.isDefault_minloc:
            self.set_minor_locator(info.minloc)
            self.isDefault_minloc = True
        if info.majfmt is not None and \
           self.major.formatter != info.majfmt and self.isDefault_majfmt:
            self.set_major_formatter(info.majfmt)
            self.isDefault_majfmt = True
        if info.minfmt is not None and \
           self.minor.formatter != info.minfmt and self.isDefault_minfmt:
            self.set_minor_formatter(info.minfmt)
            self.isDefault_minfmt = True
        if info.label is not None and self.isDefault_label:
            self.set_label_text(info.label)
            self.isDefault_label = True

        self.set_default_intervals()

    def have_units(self):
        return self._converter is not None or self.units is not None

    def convert_units(self, x):
        # If x is natively supported by Matplotlib, doesn't need converting
        if munits._is_natively_supported(x):
            return x

        if self._converter is None:
            self._set_converter(munits.registry.get_converter(x))

        if self._converter is None:
            return x
        try:
            ret = self._converter.convert(x, self.units, self)
        except Exception as e:
            raise munits.ConversionError('Failed to convert value(s) to axis '
                                         f'units: {x!r}') from e
        return ret

    def get_converter(self):
        """
        Get the unit converter for axis.

        Returns
        -------
        `~matplotlib.units.ConversionInterface` or None
        """
        return self._converter

    def set_converter(self, converter):
        """
        Set the unit converter for axis.

        Parameters
        ----------
        converter : `~matplotlib.units.ConversionInterface`
        """
        self._set_converter(converter)
        self._converter_is_explicit = True

    def _set_converter(self, converter):
        if self._converter is converter or self._converter == converter:
            return
        if self._converter_is_explicit:
            raise RuntimeError("Axis already has an explicit converter set")
        elif (
            self._converter is not None and
            not isinstance(converter, type(self._converter)) and
            not isinstance(self._converter, type(converter))
        ):
            _api.warn_external(
                "This axis already has a converter set and "
                "is updating to a potentially incompatible converter"
            )
        self._converter = converter

    def set_units(self, u):
        """
        Set the units for axis.

        Parameters
        ----------
        u : units tag

        Notes
        -----
        The units of any shared axis will also be updated.
        """
        if u == self.units:
            return
        for axis in self._get_shared_axis():
            axis.units = u
            axis._update_axisinfo()
            axis.callbacks.process('units')
            axis.stale = True

    def get_units(self):
        """Return the units for axis."""
        return self.units

    def set_label_text(self, label, fontdict=None, **kwargs):
        """
        Set the text value of the axis label.

        Parameters
        ----------
        label : str
            Text string.
        fontdict : dict
            Text properties.

            .. admonition:: Discouraged

               The use of *fontdict* is discouraged. Parameters should be passed as
               individual keyword arguments or using dictionary-unpacking
               ``set_label_text(..., **fontdict)``.

        **kwargs
            Merged into fontdict.
        """
        self.isDefault_label = False
        self.label.set_text(label)
        if fontdict is not None:
            self.label.update(fontdict)
        self.label.update(kwargs)
        self.stale = True
        return self.label

    def set_major_formatter(self, formatter):
        """
        Set the formatter of the major ticker.

        In addition to a `~matplotlib.ticker.Formatter` instance,
        this also accepts a ``str`` or function.

        For a ``str`` a `~matplotlib.ticker.StrMethodFormatter` is used.
        The field used for the value must be labeled ``'x'`` and the field used
        for the position must be labeled ``'pos'``.
        See the  `~matplotlib.ticker.StrMethodFormatter` documentation for
        more information.

        For a function, a `~matplotlib.ticker.FuncFormatter` is used.
        The function must take two inputs (a tick value ``x`` and a
        position ``pos``), and return a string containing the corresponding
        tick label.
        See the  `~matplotlib.ticker.FuncFormatter` documentation for
        more information.

        Parameters
        ----------
        formatter : `~matplotlib.ticker.Formatter`, ``str``, or function
        """
        self._set_formatter(formatter, self.major)

    def set_minor_formatter(self, formatter):
        """
        Set the formatter of the minor ticker.

        In addition to a `~matplotlib.ticker.Formatter` instance,
        this also accepts a ``str`` or function.
        See `.Axis.set_major_formatter` for more information.

        Parameters
        ----------
        formatter : `~matplotlib.ticker.Formatter`, ``str``, or function
        """
        self._set_formatter(formatter, self.minor)

    def _set_formatter(self, formatter, level):
        if isinstance(formatter, str):
            formatter = mticker.StrMethodFormatter(formatter)
        # Don't allow any other TickHelper to avoid easy-to-make errors,
        # like using a Locator instead of a Formatter.
        elif (callable(formatter) and
              not isinstance(formatter, mticker.TickHelper)):
            formatter = mticker.FuncFormatter(formatter)
        else:
            _api.check_isinstance(mticker.Formatter, formatter=formatter)

        if (isinstance(formatter, mticker.FixedFormatter)
                and len(formatter.seq) > 0
                and not isinstance(level.locator, mticker.FixedLocator)):
            _api.warn_external('FixedFormatter should only be used together '
                               'with FixedLocator')

        if level == self.major:
            self.isDefault_majfmt = False
        else:
            self.isDefault_minfmt = False

        level.formatter = formatter
        formatter.set_axis(self)
        self.stale = True

    def set_major_locator(self, locator):
        """
        Set the locator of the major ticker.

        Parameters
        ----------
        locator : `~matplotlib.ticker.Locator`
        """
        _api.check_isinstance(mticker.Locator, locator=locator)
        self.isDefault_majloc = False
        self.major.locator = locator
        if self.major.formatter:
            self.major.formatter._set_locator(locator)
        locator.set_axis(self)
        self.stale = True

    def set_minor_locator(self, locator):
        """
        Set the locator of the minor ticker.

        Parameters
        ----------
        locator : `~matplotlib.ticker.Locator`
        """
        _api.check_isinstance(mticker.Locator, locator=locator)
        self.isDefault_minloc = False
        self.minor.locator = locator
        if self.minor.formatter:
            self.minor.formatter._set_locator(locator)
        locator.set_axis(self)
        self.stale = True

    def set_pickradius(self, pickradius):
        """
        Set the depth of the axis used by the picker.

        Parameters
        ----------
        pickradius : float
            The acceptance radius for containment tests.
            See also `.Axis.contains`.
        """
        if not isinstance(pickradius, Real) or pickradius < 0:
            raise ValueError("pick radius should be a distance")
        self._pickradius = pickradius

    pickradius = property(
        get_pickradius, set_pickradius, doc="The acceptance radius for "
        "containment tests. See also `.Axis.contains`.")

    # Helper for set_ticklabels. Defining it here makes it picklable.
    @staticmethod
    def _format_with_dict(tickd, x, pos):
        return tickd.get(x, "")

    def set_ticklabels(self, labels, *, minor=False, fontdict=None, **kwargs):
        r"""
        [*Discouraged*] Set this Axis' tick labels with list of string labels.

        .. admonition:: Discouraged

            The use of this method is discouraged, because of the dependency on
            tick positions. In most cases, you'll want to use
            ``Axes.set_[x/y/z]ticks(positions, labels)`` or ``Axis.set_ticks``
            instead.

            If you are using this method, you should always fix the tick
            positions before, e.g. by using `.Axis.set_ticks` or by explicitly
            setting a `~.ticker.FixedLocator`. Otherwise, ticks are free to
            move and the labels may end up in unexpected positions.

        Parameters
        ----------
        labels : sequence of str or of `.Text`\s
            Texts for labeling each tick location in the sequence set by
            `.Axis.set_ticks`; the number of labels must match the number of locations.
            The labels are used as is, via a `.FixedFormatter` (without further
            formatting).

        minor : bool
            If True, set minor ticks instead of major ticks.

        fontdict : dict, optional

            .. admonition:: Discouraged

               The use of *fontdict* is discouraged. Parameters should be passed as
               individual keyword arguments or using dictionary-unpacking
               ``set_ticklabels(..., **fontdict)``.

            A dictionary controlling the appearance of the ticklabels.
            The default *fontdict* is::

               {'fontsize': rcParams['axes.titlesize'],
                'fontweight': rcParams['axes.titleweight'],
                'verticalalignment': 'baseline',
                'horizontalalignment': loc}

        **kwargs
            Text properties.

            .. warning::

                This only sets the properties of the current ticks, which is
                only sufficient for static plots.

                Ticks are not guaranteed to be persistent. Various operations
                can create, delete and modify the Tick instances. There is an
                imminent risk that these settings can get lost if you work on
                the figure further (including also panning/zooming on a
                displayed figure).

                Use `.set_tick_params` instead if possible.

        Returns
        -------
        list of `.Text`\s
            For each tick, includes ``tick.label1`` if it is visible, then
            ``tick.label2`` if it is visible, in that order.
        """
        try:
            labels = [t.get_text() if hasattr(t, 'get_text') else t
                      for t in labels]
        except TypeError:
            raise TypeError(f"{labels:=} must be a sequence") from None
        locator = (self.get_minor_locator() if minor
                   else self.get_major_locator())
        if not labels:
            # eg labels=[]:
            formatter = mticker.NullFormatter()
        elif isinstance(locator, mticker.FixedLocator):
            # Passing [] as a list of labels is often used as a way to
            # remove all tick labels, so only error for > 0 labels
            if len(locator.locs) != len(labels) and len(labels) != 0:
                raise ValueError(
                    "The number of FixedLocator locations"
                    f" ({len(locator.locs)}), usually from a call to"
                    " set_ticks, does not match"
                    f" the number of labels ({len(labels)}).")
            tickd = {loc: lab for loc, lab in zip(locator.locs, labels)}
            func = functools.partial(self._format_with_dict, tickd)
            formatter = mticker.FuncFormatter(func)
        else:
            _api.warn_external(
                 "set_ticklabels() should only be used with a fixed number of "
                 "ticks, i.e. after set_ticks() or using a FixedLocator.")
            formatter = mticker.FixedFormatter(labels)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="FixedFormatter should only be used together with FixedLocator")
            if minor:
                self.set_minor_formatter(formatter)
                locs = self.get_minorticklocs()
                ticks = self.get_minor_ticks(len(locs))
            else:
                self.set_major_formatter(formatter)
                locs = self.get_majorticklocs()
                ticks = self.get_major_ticks(len(locs))

        ret = []
        if fontdict is not None:
            kwargs.update(fontdict)
        for pos, (loc, tick) in enumerate(zip(locs, ticks)):
            tick.update_position(loc)
            tick_label = formatter(loc, pos)
            # deal with label1
            tick.label1.set_text(tick_label)
            tick.label1._internal_update(kwargs)
            # deal with label2
            tick.label2.set_text(tick_label)
            tick.label2._internal_update(kwargs)
            # only return visible tick labels
            if tick.label1.get_visible():
                ret.append(tick.label1)
            if tick.label2.get_visible():
                ret.append(tick.label2)

        self.stale = True
        return ret

    def _set_tick_locations(self, ticks, *, minor=False):
        # see docstring of set_ticks

        # XXX if the user changes units, the information will be lost here
        ticks = self.convert_units(ticks)
        locator = mticker.FixedLocator(ticks)  # validate ticks early.
        if len(ticks):
            for axis in self._get_shared_axis():
                # set_view_interval maintains any preexisting inversion.
                axis.set_view_interval(min(ticks), max(ticks))
        self.axes.stale = True
        if minor:
            self.set_minor_locator(locator)
            return self.get_minor_ticks(len(ticks))
        else:
            self.set_major_locator(locator)
            return self.get_major_ticks(len(ticks))

    def set_ticks(self, ticks, labels=None, *, minor=False, **kwargs):
        """
        Set this Axis' tick locations and optionally tick labels.

        If necessary, the view limits of the Axis are expanded so that all
        given ticks are visible.

        Parameters
        ----------
        ticks : 1D array-like
            Array of tick locations (either floats or in axis units). The axis
            `.Locator` is replaced by a `~.ticker.FixedLocator`.

            Pass an empty list (``set_ticks([])``) to remove all ticks.

            Some tick formatters will not label arbitrary tick positions;
            e.g. log formatters only label decade ticks by default. In
            such a case you can set a formatter explicitly on the axis
            using `.Axis.set_major_formatter` or provide formatted
            *labels* yourself.

        labels : list of str, optional
            Tick labels for each location in *ticks*; must have the same length as
            *ticks*. If set, the labels are used as is, via a `.FixedFormatter`.
            If not set, the labels are generated using the axis tick `.Formatter`.

        minor : bool, default: False
            If ``False``, set only the major ticks; if ``True``, only the minor ticks.

        **kwargs
            `.Text` properties for the labels. Using these is only allowed if
            you pass *labels*. In other cases, please use `~.Axes.tick_params`.

        Notes
        -----
        The mandatory expansion of the view limits is an intentional design
        choice to prevent the surprise of a non-visible tick. If you need
        other limits, you should set the limits explicitly after setting the
        ticks.
        """
        if labels is None and kwargs:
            first_key = next(iter(kwargs))
            raise ValueError(
                f"Incorrect use of keyword argument {first_key!r}. Keyword arguments "
                "other than 'minor' modify the text labels and can only be used if "
                "'labels' are passed as well.")
        result = self._set_tick_locations(ticks, minor=minor)
        if labels is not None:
            self.set_ticklabels(labels, minor=minor, **kwargs)
        return result

    def _get_tick_boxes_siblings(self, renderer):
        """
        Get the bounding boxes for this `.axis` and its siblings
        as set by `.Figure.align_xlabels` or  `.Figure.align_ylabels`.

        By default, it just gets bboxes for *self*.
        """
        # Get the Grouper keeping track of x or y label groups for this figure.
        name = self._get_axis_name()
        if name not in self.get_figure(root=False)._align_label_groups:
            return [], []
        grouper = self.get_figure(root=False)._align_label_groups[name]
        bboxes = []
        bboxes2 = []
        # If we want to align labels from other Axes:
        for ax in grouper.get_siblings(self.axes):
            axis = ax._axis_map[name]
            ticks_to_draw = axis._update_ticks()
            tlb, tlb2 = axis._get_ticklabel_bboxes(ticks_to_draw, renderer)
            bboxes.extend(tlb)
            bboxes2.extend(tlb2)
        return bboxes, bboxes2

    def _update_label_position(self, renderer):
        """
        Update the label position based on the bounding box enclosing
        all the ticklabels and axis spine.
        """
        raise NotImplementedError('Derived must override')

    def _update_offset_text_position(self, bboxes, bboxes2):
        """
        Update the offset text position based on the sequence of bounding
        boxes of all the ticklabels.
        """
        raise NotImplementedError('Derived must override')

    def axis_date(self, tz=None):
        """
        Set up axis ticks and labels to treat data along this Axis as dates.

        Parameters
        ----------
        tz : str or `datetime.tzinfo`, default: :rc:`timezone`
            The timezone used to create date labels.
        """
        # By providing a sample datetime instance with the desired timezone,
        # the registered converter can be selected, and the "units" attribute,
        # which is the timezone, can be set.
        if isinstance(tz, str):
            import dateutil.tz
            tz = dateutil.tz.gettz(tz)
        self.update_units(datetime.datetime(2009, 1, 1, 0, 0, 0, 0, tz))

    def get_tick_space(self):
        """Return the estimated number of ticks that can fit on the axis."""
        # Must be overridden in the subclass
        raise NotImplementedError()

    def _get_ticks_position(self):
        """
        Helper for `XAxis.get_ticks_position` and `YAxis.get_ticks_position`.

        Check the visibility of tick1line, label1, tick2line, and label2 on
        the first major and the first minor ticks, and return

        - 1 if only tick1line and label1 are visible (which corresponds to
          "bottom" for the x-axis and "left" for the y-axis);
        - 2 if only tick2line and label2 are visible (which corresponds to
          "top" for the x-axis and "right" for the y-axis);
        - "default" if only tick1line, tick2line and label1 are visible;
        - "unknown" otherwise.
        """
        major = self.majorTicks[0]
        minor = self.minorTicks[0]
        if all(tick.tick1line.get_visible()
               and not tick.tick2line.get_visible()
               and tick.label1.get_visible()
               and not tick.label2.get_visible()
               for tick in [major, minor]):
            return 1
        elif all(tick.tick2line.get_visible()
                 and not tick.tick1line.get_visible()
                 and tick.label2.get_visible()
                 and not tick.label1.get_visible()
                 for tick in [major, minor]):
            return 2
        elif all(tick.tick1line.get_visible()
                 and tick.tick2line.get_visible()
                 and tick.label1.get_visible()
                 and not tick.label2.get_visible()
                 for tick in [major, minor]):
            return "default"
        else:
            return "unknown"

    def get_label_position(self):
        """
        Return the label position (top or bottom)
        """
        return self.label_position

    def set_label_position(self, position):
        """
        Set the label position (top or bottom)

        Parameters
        ----------
        position : {'top', 'bottom'}
        """
        raise NotImplementedError()

    def get_minpos(self):
        raise NotImplementedError()


def _make_getset_interval(method_name, lim_name, attr_name):
    """
    Helper to generate ``get_{data,view}_interval`` and
    ``set_{data,view}_interval`` implementations.
    """

    def getter(self):
        # docstring inherited.
        return getattr(getattr(self.axes, lim_name), attr_name)

    def setter(self, vmin, vmax, ignore=False):
        # docstring inherited.
        if ignore:
            setattr(getattr(self.axes, lim_name), attr_name, (vmin, vmax))
        else:
            oldmin, oldmax = getter(self)
            if oldmin < oldmax:
                setter(self, min(vmin, vmax, oldmin), max(vmin, vmax, oldmax),
                       ignore=True)
            else:
                setter(self, max(vmin, vmax, oldmin), min(vmin, vmax, oldmax),
                       ignore=True)
        self.stale = True

    getter.__name__ = f"get_{method_name}_interval"
    setter.__name__ = f"set_{method_name}_interval"

    return getter, setter


class XAxis(Axis):
    __name__ = 'xaxis'
    axis_name = 'x'  #: Read-only name identifying the axis.
    _tick_class = XTick

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init()

    def _init(self):
        """
        Initialize the label and offsetText instance values and
        `label_position` / `offset_text_position`.
        """
        # x in axes coords, y in display coords (to be updated at draw time by
        # _update_label_positions and _update_offset_text_position).
        self.label.set(
            x=0.5, y=0,
            verticalalignment='top', horizontalalignment='center',
            transform=mtransforms.blended_transform_factory(
                self.axes.transAxes, mtransforms.IdentityTransform()),
        )
        self.label_position = 'bottom'

        if mpl.rcParams['xtick.labelcolor'] == 'inherit':
            tick_color = mpl.rcParams['xtick.color']
        else:
            tick_color = mpl.rcParams['xtick.labelcolor']

        self.offsetText.set(
            x=1, y=0,
            verticalalignment='top', horizontalalignment='right',
            transform=mtransforms.blended_transform_factory(
                self.axes.transAxes, mtransforms.IdentityTransform()),
            fontsize=mpl.rcParams['xtick.labelsize'],
            color=tick_color
        )
        self.offset_text_position = 'bottom'

    def contains(self, mouseevent):
        """Test whether the mouse event occurred in the x-axis."""
        if self._different_canvas(mouseevent):
            return False, {}
        x, y = mouseevent.x, mouseevent.y
        try:
            trans = self.axes.transAxes.inverted()
            xaxes, yaxes = trans.transform((x, y))
        except ValueError:
            return False, {}
        (l, b), (r, t) = self.axes.transAxes.transform([(0, 0), (1, 1)])
        inaxis = 0 <= xaxes <= 1 and (
            b - self._pickradius < y < b or
            t < y < t + self._pickradius)
        return inaxis, {}

    def set_label_position(self, position):
        """
        Set the label position (top or bottom)

        Parameters
        ----------
        position : {'top', 'bottom'}
        """
        self.label.set_verticalalignment(_api.check_getitem({
            'top': 'baseline', 'bottom': 'top',
        }, position=position))
        self.label_position = position
        self.stale = True

    def _update_label_position(self, renderer):
        """
        Update the label position based on the bounding box enclosing
        all the ticklabels and axis spine
        """
        if not self._autolabelpos:
            return

        # get bounding boxes for this axis and any siblings
        # that have been set by `fig.align_xlabels()`
        bboxes, bboxes2 = self._get_tick_boxes_siblings(renderer=renderer)
        x, y = self.label.get_position()

        if self.label_position == 'bottom':
            # Union with extents of the bottom spine if present, of the axes otherwise.
            bbox = mtransforms.Bbox.union([
                *bboxes, self.axes.spines.get("bottom", self.axes).get_window_extent()])
            self.label.set_position(
                (x, bbox.y0 - self.labelpad * self.get_figure(root=True).dpi / 72))
        else:
            # Union with extents of the top spine if present, of the axes otherwise.
            bbox = mtransforms.Bbox.union([
                *bboxes2, self.axes.spines.get("top", self.axes).get_window_extent()])
            self.label.set_position(
                (x, bbox.y1 + self.labelpad * self.get_figure(root=True).dpi / 72))

    def _update_offset_text_position(self, bboxes, bboxes2):
        """
        Update the offset_text position based on the sequence of bounding
        boxes of all the ticklabels
        """
        x, y = self.offsetText.get_position()
        if not hasattr(self, '_tick_position'):
            self._tick_position = 'bottom'
        if self._tick_position == 'bottom':
            if not len(bboxes):
                bottom = self.axes.bbox.ymin
            else:
                bbox = mtransforms.Bbox.union(bboxes)
                bottom = bbox.y0
            y = bottom - self.OFFSETTEXTPAD * self.get_figure(root=True).dpi / 72
        else:
            if not len(bboxes2):
                top = self.axes.bbox.ymax
            else:
                bbox = mtransforms.Bbox.union(bboxes2)
                top = bbox.y1
            y = top + self.OFFSETTEXTPAD * self.get_figure(root=True).dpi / 72
        self.offsetText.set_position((x, y))

    def set_ticks_position(self, position):
        """
        Set the ticks position.

        Parameters
        ----------
        position : {'top', 'bottom', 'both', 'default', 'none'}
            'both' sets the ticks to appear on both positions, but does not
            change the tick labels.  'default' resets the tick positions to
            the default: ticks on both positions, labels at bottom.  'none'
            can be used if you don't want any ticks. 'none' and 'both'
            affect only the ticks, not the labels.
        """
        if position == 'top':
            self.set_tick_params(which='both', top=True, labeltop=True,
                                 bottom=False, labelbottom=False)
            self._tick_position = 'top'
            self.offsetText.set_verticalalignment('bottom')
        elif position == 'bottom':
            self.set_tick_params(which='both', top=False, labeltop=False,
                                 bottom=True, labelbottom=True)
            self._tick_position = 'bottom'
            self.offsetText.set_verticalalignment('top')
        elif position == 'both':
            self.set_tick_params(which='both', top=True,
                                 bottom=True)
        elif position == 'none':
            self.set_tick_params(which='both', top=False,
                                 bottom=False)
        elif position == 'default':
            self.set_tick_params(which='both', top=True, labeltop=False,
                                 bottom=True, labelbottom=True)
            self._tick_position = 'bottom'
            self.offsetText.set_verticalalignment('top')
        else:
            _api.check_in_list(['top', 'bottom', 'both', 'default', 'none'],
                               position=position)
        self.stale = True

    def tick_top(self):
        """
        Move ticks and ticklabels (if present) to the top of the Axes.
        """
        label = True
        if 'label1On' in self._major_tick_kw:
            label = (self._major_tick_kw['label1On']
                     or self._major_tick_kw['label2On'])
        self.set_ticks_position('top')
        # If labels were turned off before this was called, leave them off.
        self.set_tick_params(which='both', labeltop=label)

    def tick_bottom(self):
        """
        Move ticks and ticklabels (if present) to the bottom of the Axes.
        """
        label = True
        if 'label1On' in self._major_tick_kw:
            label = (self._major_tick_kw['label1On']
                     or self._major_tick_kw['label2On'])
        self.set_ticks_position('bottom')
        # If labels were turned off before this was called, leave them off.
        self.set_tick_params(which='both', labelbottom=label)

    def get_ticks_position(self):
        """
        Return the ticks position ("top", "bottom", "default", or "unknown").
        """
        return {1: "bottom", 2: "top",
                "default": "default", "unknown": "unknown"}[
                    self._get_ticks_position()]

    get_view_interval, set_view_interval = _make_getset_interval(
        "view", "viewLim", "intervalx")
    get_data_interval, set_data_interval = _make_getset_interval(
        "data", "dataLim", "intervalx")

    def get_minpos(self):
        return self.axes.dataLim.minposx

    def set_default_intervals(self):
        # docstring inherited
        # only change view if dataLim has not changed and user has
        # not changed the view:
        if (not self.axes.dataLim.mutatedx() and
                not self.axes.viewLim.mutatedx()):
            if self._converter is not None:
                info = self._converter.axisinfo(self.units, self)
                if info.default_limits is not None:
                    xmin, xmax = self.convert_units(info.default_limits)
                    self.axes.viewLim.intervalx = xmin, xmax
        self.stale = True

    def get_tick_space(self):
        ends = mtransforms.Bbox.unit().transformed(
            self.axes.transAxes - self.get_figure(root=False).dpi_scale_trans)
        length = ends.width * 72
        # There is a heuristic here that the aspect ratio of tick text
        # is no more than 3:1
        size = self._get_tick_label_size('x') * 3
        if size > 0:
            return int(np.floor(length / size))
        else:
            return 2**31 - 1


class YAxis(Axis):
    __name__ = 'yaxis'
    axis_name = 'y'  #: Read-only name identifying the axis.
    _tick_class = YTick

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init()

    def _init(self):
        """
        Initialize the label and offsetText instance values and
        `label_position` / `offset_text_position`.
        """
        # x in display coords, y in axes coords (to be updated at draw time by
        # _update_label_positions and _update_offset_text_position).
        self.label.set(
            x=0, y=0.5,
            verticalalignment='bottom', horizontalalignment='center',
            rotation='vertical', rotation_mode='anchor',
            transform=mtransforms.blended_transform_factory(
                mtransforms.IdentityTransform(), self.axes.transAxes),
        )
        self.label_position = 'left'

        if mpl.rcParams['ytick.labelcolor'] == 'inherit':
            tick_color = mpl.rcParams['ytick.color']
        else:
            tick_color = mpl.rcParams['ytick.labelcolor']

        # x in axes coords, y in display coords(!).
        self.offsetText.set(
            x=0, y=0.5,
            verticalalignment='baseline', horizontalalignment='left',
            transform=mtransforms.blended_transform_factory(
                self.axes.transAxes, mtransforms.IdentityTransform()),
            fontsize=mpl.rcParams['ytick.labelsize'],
            color=tick_color
        )
        self.offset_text_position = 'left'

    def contains(self, mouseevent):
        # docstring inherited
        if self._different_canvas(mouseevent):
            return False, {}
        x, y = mouseevent.x, mouseevent.y
        try:
            trans = self.axes.transAxes.inverted()
            xaxes, yaxes = trans.transform((x, y))
        except ValueError:
            return False, {}
        (l, b), (r, t) = self.axes.transAxes.transform([(0, 0), (1, 1)])
        inaxis = 0 <= yaxes <= 1 and (
            l - self._pickradius < x < l or
            r < x < r + self._pickradius)
        return inaxis, {}

    def set_label_position(self, position):
        """
        Set the label position (left or right)

        Parameters
        ----------
        position : {'left', 'right'}
        """
        self.label.set_rotation_mode('anchor')
        self.label.set_verticalalignment(_api.check_getitem({
            'left': 'bottom', 'right': 'top',
        }, position=position))
        self.label_position = position
        self.stale = True

    def _update_label_position(self, renderer):
        """
        Update the label position based on the bounding box enclosing
        all the ticklabels and axis spine
        """
        if not self._autolabelpos:
            return

        # get bounding boxes for this axis and any siblings
        # that have been set by `fig.align_ylabels()`
        bboxes, bboxes2 = self._get_tick_boxes_siblings(renderer=renderer)
        x, y = self.label.get_position()

        if self.label_position == 'left':
            # Union with extents of the left spine if present, of the axes otherwise.
            bbox = mtransforms.Bbox.union([
                *bboxes, self.axes.spines.get("left", self.axes).get_window_extent()])
            self.label.set_position(
                (bbox.x0 - self.labelpad * self.get_figure(root=True).dpi / 72, y))
        else:
            # Union with extents of the right spine if present, of the axes otherwise.
            bbox = mtransforms.Bbox.union([
                *bboxes2, self.axes.spines.get("right", self.axes).get_window_extent()])
            self.label.set_position(
                (bbox.x1 + self.labelpad * self.get_figure(root=True).dpi / 72, y))

    def _update_offset_text_position(self, bboxes, bboxes2):
        """
        Update the offset_text position based on the sequence of bounding
        boxes of all the ticklabels
        """
        x, _ = self.offsetText.get_position()
        if 'outline' in self.axes.spines:
            # Special case for colorbars:
            bbox = self.axes.spines['outline'].get_window_extent()
        else:
            bbox = self.axes.bbox
        top = bbox.ymax
        self.offsetText.set_position(
            (x, top + self.OFFSETTEXTPAD * self.get_figure(root=True).dpi / 72)
        )

    def set_offset_position(self, position):
        """
        Parameters
        ----------
        position : {'left', 'right'}
        """
        x, y = self.offsetText.get_position()
        x = _api.check_getitem({'left': 0, 'right': 1}, position=position)

        self.offsetText.set_ha(position)
        self.offsetText.set_position((x, y))
        self.stale = True

    def set_ticks_position(self, position):
        """
        Set the ticks position.

        Parameters
        ----------
        position : {'left', 'right', 'both', 'default', 'none'}
            'both' sets the ticks to appear on both positions, but does not
            change the tick labels.  'default' resets the tick positions to
            the default: ticks on both positions, labels at left.  'none'
            can be used if you don't want any ticks. 'none' and 'both'
            affect only the ticks, not the labels.
        """
        if position == 'right':
            self.set_tick_params(which='both', right=True, labelright=True,
                                 left=False, labelleft=False)
            self.set_offset_position(position)
        elif position == 'left':
            self.set_tick_params(which='both', right=False, labelright=False,
                                 left=True, labelleft=True)
            self.set_offset_position(position)
        elif position == 'both':
            self.set_tick_params(which='both', right=True,
                                 left=True)
        elif position == 'none':
            self.set_tick_params(which='both', right=False,
                                 left=False)
        elif position == 'default':
            self.set_tick_params(which='both', right=True, labelright=False,
                                 left=True, labelleft=True)
        else:
            _api.check_in_list(['left', 'right', 'both', 'default', 'none'],
                               position=position)
        self.stale = True

    def tick_right(self):
        """
        Move ticks and ticklabels (if present) to the right of the Axes.
        """
        label = True
        if 'label1On' in self._major_tick_kw:
            label = (self._major_tick_kw['label1On']
                     or self._major_tick_kw['label2On'])
        self.set_ticks_position('right')
        # if labels were turned off before this was called
        # leave them off
        self.set_tick_params(which='both', labelright=label)

    def tick_left(self):
        """
        Move ticks and ticklabels (if present) to the left of the Axes.
        """
        label = True
        if 'label1On' in self._major_tick_kw:
            label = (self._major_tick_kw['label1On']
                     or self._major_tick_kw['label2On'])
        self.set_ticks_position('left')
        # if labels were turned off before this was called
        # leave them off
        self.set_tick_params(which='both', labelleft=label)

    def get_ticks_position(self):
        """
        Return the ticks position ("left", "right", "default", or "unknown").
        """
        return {1: "left", 2: "right",
                "default": "default", "unknown": "unknown"}[
                    self._get_ticks_position()]

    get_view_interval, set_view_interval = _make_getset_interval(
        "view", "viewLim", "intervaly")
    get_data_interval, set_data_interval = _make_getset_interval(
        "data", "dataLim", "intervaly")

    def get_minpos(self):
        return self.axes.dataLim.minposy

    def set_default_intervals(self):
        # docstring inherited
        # only change view if dataLim has not changed and user has
        # not changed the view:
        if (not self.axes.dataLim.mutatedy() and
                not self.axes.viewLim.mutatedy()):
            if self._converter is not None:
                info = self._converter.axisinfo(self.units, self)
                if info.default_limits is not None:
                    ymin, ymax = self.convert_units(info.default_limits)
                    self.axes.viewLim.intervaly = ymin, ymax
        self.stale = True

    def get_tick_space(self):
        ends = mtransforms.Bbox.unit().transformed(
            self.axes.transAxes - self.get_figure(root=False).dpi_scale_trans)
        length = ends.height * 72
        # Having a spacing of at least 2 just looks good.
        size = self._get_tick_label_size('y') * 2
        if size > 0:
            return int(np.floor(length / size))
        else:
            return 2**31 - 1

# === NexusCore/openenv\Lib\site-packages\anyio\_backends\_asyncio.py ===
from __future__ import annotations

import array
import asyncio
import concurrent.futures
import contextvars
import math
import os
import socket
import sys
import threading
import weakref
from asyncio import (
    AbstractEventLoop,
    CancelledError,
    all_tasks,
    create_task,
    current_task,
    get_running_loop,
    sleep,
)
from asyncio.base_events import _run_until_complete_cb  # type: ignore[attr-defined]
from collections import OrderedDict, deque
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Iterable,
    Sequence,
)
from concurrent.futures import Future
from contextlib import AbstractContextManager, suppress
from contextvars import Context, copy_context
from dataclasses import dataclass
from functools import partial, wraps
from inspect import (
    CORO_RUNNING,
    CORO_SUSPENDED,
    getcoroutinestate,
    iscoroutine,
)
from io import IOBase
from os import PathLike
from queue import Queue
from signal import Signals
from socket import AddressFamily, SocketKind
from threading import Thread
from types import CodeType, TracebackType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Optional,
    TypeVar,
    cast,
)
from weakref import WeakKeyDictionary

import sniffio

from .. import (
    CapacityLimiterStatistics,
    EventStatistics,
    LockStatistics,
    TaskInfo,
    abc,
)
from .._core._eventloop import claim_worker_thread, threadlocals
from .._core._exceptions import (
    BrokenResourceError,
    BusyResourceError,
    ClosedResourceError,
    EndOfStream,
    WouldBlock,
    iterate_exceptions,
)
from .._core._sockets import convert_ipv6_sockaddr
from .._core._streams import create_memory_object_stream
from .._core._synchronization import (
    CapacityLimiter as BaseCapacityLimiter,
)
from .._core._synchronization import Event as BaseEvent
from .._core._synchronization import Lock as BaseLock
from .._core._synchronization import (
    ResourceGuard,
    SemaphoreStatistics,
)
from .._core._synchronization import Semaphore as BaseSemaphore
from .._core._tasks import CancelScope as BaseCancelScope
from ..abc import (
    AsyncBackend,
    IPSockAddrType,
    SocketListener,
    UDPPacketType,
    UNIXDatagramPacketType,
)
from ..abc._eventloop import StrOrBytesPath
from ..lowlevel import RunVar
from ..streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

if TYPE_CHECKING:
    from _typeshed import FileDescriptorLike
else:
    FileDescriptorLike = object

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 11):
    from asyncio import Runner
    from typing import TypeVarTuple, Unpack
else:
    import contextvars
    import enum
    import signal
    from asyncio import coroutines, events, exceptions, tasks

    from exceptiongroup import BaseExceptionGroup
    from typing_extensions import TypeVarTuple, Unpack

    class _State(enum.Enum):
        CREATED = "created"
        INITIALIZED = "initialized"
        CLOSED = "closed"

    class Runner:
        # Copied from CPython 3.11
        def __init__(
            self,
            *,
            debug: bool | None = None,
            loop_factory: Callable[[], AbstractEventLoop] | None = None,
        ):
            self._state = _State.CREATED
            self._debug = debug
            self._loop_factory = loop_factory
            self._loop: AbstractEventLoop | None = None
            self._context = None
            self._interrupt_count = 0
            self._set_event_loop = False

        def __enter__(self) -> Runner:
            self._lazy_init()
            return self

        def __exit__(
            self,
            exc_type: type[BaseException],
            exc_val: BaseException,
            exc_tb: TracebackType,
        ) -> None:
            self.close()

        def close(self) -> None:
            """Shutdown and close event loop."""
            if self._state is not _State.INITIALIZED:
                return
            try:
                loop = self._loop
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
                if hasattr(loop, "shutdown_default_executor"):
                    loop.run_until_complete(loop.shutdown_default_executor())
                else:
                    loop.run_until_complete(_shutdown_default_executor(loop))
            finally:
                if self._set_event_loop:
                    events.set_event_loop(None)
                loop.close()
                self._loop = None
                self._state = _State.CLOSED

        def get_loop(self) -> AbstractEventLoop:
            """Return embedded event loop."""
            self._lazy_init()
            return self._loop

        def run(self, coro: Coroutine[T_Retval], *, context=None) -> T_Retval:
            """Run a coroutine inside the embedded event loop."""
            if not coroutines.iscoroutine(coro):
                raise ValueError(f"a coroutine was expected, got {coro!r}")

            if events._get_running_loop() is not None:
                # fail fast with short traceback
                raise RuntimeError(
                    "Runner.run() cannot be called from a running event loop"
                )

            self._lazy_init()

            if context is None:
                context = self._context
            task = context.run(self._loop.create_task, coro)

            if (
                threading.current_thread() is threading.main_thread()
                and signal.getsignal(signal.SIGINT) is signal.default_int_handler
            ):
                sigint_handler = partial(self._on_sigint, main_task=task)
                try:
                    signal.signal(signal.SIGINT, sigint_handler)
                except ValueError:
                    # `signal.signal` may throw if `threading.main_thread` does
                    # not support signals (e.g. embedded interpreter with signals
                    # not registered - see gh-91880)
                    sigint_handler = None
            else:
                sigint_handler = None

            self._interrupt_count = 0
            try:
                return self._loop.run_until_complete(task)
            except exceptions.CancelledError:
                if self._interrupt_count > 0:
                    uncancel = getattr(task, "uncancel", None)
                    if uncancel is not None and uncancel() == 0:
                        raise KeyboardInterrupt()
                raise  # CancelledError
            finally:
                if (
                    sigint_handler is not None
                    and signal.getsignal(signal.SIGINT) is sigint_handler
                ):
                    signal.signal(signal.SIGINT, signal.default_int_handler)

        def _lazy_init(self) -> None:
            if self._state is _State.CLOSED:
                raise RuntimeError("Runner is closed")
            if self._state is _State.INITIALIZED:
                return
            if self._loop_factory is None:
                self._loop = events.new_event_loop()
                if not self._set_event_loop:
                    # Call set_event_loop only once to avoid calling
                    # attach_loop multiple times on child watchers
                    events.set_event_loop(self._loop)
                    self._set_event_loop = True
            else:
                self._loop = self._loop_factory()
            if self._debug is not None:
                self._loop.set_debug(self._debug)
            self._context = contextvars.copy_context()
            self._state = _State.INITIALIZED

        def _on_sigint(self, signum, frame, main_task: asyncio.Task) -> None:
            self._interrupt_count += 1
            if self._interrupt_count == 1 and not main_task.done():
                main_task.cancel()
                # wakeup loop if it is blocked by select() with long timeout
                self._loop.call_soon_threadsafe(lambda: None)
                return
            raise KeyboardInterrupt()

    def _cancel_all_tasks(loop: AbstractEventLoop) -> None:
        to_cancel = tasks.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(tasks.gather(*to_cancel, return_exceptions=True))

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler(
                    {
                        "message": "unhandled exception during asyncio.run() shutdown",
                        "exception": task.exception(),
                        "task": task,
                    }
                )

    async def _shutdown_default_executor(loop: AbstractEventLoop) -> None:
        """Schedule the shutdown of the default executor."""

        def _do_shutdown(future: asyncio.futures.Future) -> None:
            try:
                loop._default_executor.shutdown(wait=True)  # type: ignore[attr-defined]
                loop.call_soon_threadsafe(future.set_result, None)
            except Exception as ex:
                loop.call_soon_threadsafe(future.set_exception, ex)

        loop._executor_shutdown_called = True
        if loop._default_executor is None:
            return
        future = loop.create_future()
        thread = threading.Thread(target=_do_shutdown, args=(future,))
        thread.start()
        try:
            await future
        finally:
            thread.join()


T_Retval = TypeVar("T_Retval")
T_contra = TypeVar("T_contra", contravariant=True)
PosArgsT = TypeVarTuple("PosArgsT")
P = ParamSpec("P")

_root_task: RunVar[asyncio.Task | None] = RunVar("_root_task")


def find_root_task() -> asyncio.Task:
    root_task = _root_task.get(None)
    if root_task is not None and not root_task.done():
        return root_task

    # Look for a task that has been started via run_until_complete()
    for task in all_tasks():
        if task._callbacks and not task.done():
            callbacks = [cb for cb, context in task._callbacks]
            for cb in callbacks:
                if (
                    cb is _run_until_complete_cb
                    or getattr(cb, "__module__", None) == "uvloop.loop"
                ):
                    _root_task.set(task)
                    return task

    # Look up the topmost task in the AnyIO task tree, if possible
    task = cast(asyncio.Task, current_task())
    state = _task_states.get(task)
    if state:
        cancel_scope = state.cancel_scope
        while cancel_scope and cancel_scope._parent_scope is not None:
            cancel_scope = cancel_scope._parent_scope

        if cancel_scope is not None:
            return cast(asyncio.Task, cancel_scope._host_task)

    return task


def get_callable_name(func: Callable) -> str:
    module = getattr(func, "__module__", None)
    qualname = getattr(func, "__qualname__", None)
    return ".".join([x for x in (module, qualname) if x])


#
# Event loop
#

_run_vars: WeakKeyDictionary[asyncio.AbstractEventLoop, Any] = WeakKeyDictionary()


def _task_started(task: asyncio.Task) -> bool:
    """Return ``True`` if the task has been started and has not finished."""
    # The task coro should never be None here, as we never add finished tasks to the
    # task list
    coro = task.get_coro()
    assert coro is not None
    try:
        return getcoroutinestate(coro) in (CORO_RUNNING, CORO_SUSPENDED)
    except AttributeError:
        # task coro is async_genenerator_asend https://bugs.python.org/issue37771
        raise Exception(f"Cannot determine if task {task} has started or not") from None


#
# Timeouts and cancellation
#


def is_anyio_cancellation(exc: CancelledError) -> bool:
    # Sometimes third party frameworks catch a CancelledError and raise a new one, so as
    # a workaround we have to look at the previous ones in __context__ too for a
    # matching cancel message
    while True:
        if (
            exc.args
            and isinstance(exc.args[0], str)
            and exc.args[0].startswith("Cancelled by cancel scope ")
        ):
            return True

        if isinstance(exc.__context__, CancelledError):
            exc = exc.__context__
            continue

        return False


class CancelScope(BaseCancelScope):
    def __new__(
        cls, *, deadline: float = math.inf, shield: bool = False
    ) -> CancelScope:
        return object.__new__(cls)

    def __init__(self, deadline: float = math.inf, shield: bool = False):
        self._deadline = deadline
        self._shield = shield
        self._parent_scope: CancelScope | None = None
        self._child_scopes: set[CancelScope] = set()
        self._cancel_called = False
        self._cancelled_caught = False
        self._active = False
        self._timeout_handle: asyncio.TimerHandle | None = None
        self._cancel_handle: asyncio.Handle | None = None
        self._tasks: set[asyncio.Task] = set()
        self._host_task: asyncio.Task | None = None
        if sys.version_info >= (3, 11):
            self._pending_uncancellations: int | None = 0
        else:
            self._pending_uncancellations = None

    def __enter__(self) -> CancelScope:
        if self._active:
            raise RuntimeError(
                "Each CancelScope may only be used for a single 'with' block"
            )

        self._host_task = host_task = cast(asyncio.Task, current_task())
        self._tasks.add(host_task)
        try:
            task_state = _task_states[host_task]
        except KeyError:
            task_state = TaskState(None, self)
            _task_states[host_task] = task_state
        else:
            self._parent_scope = task_state.cancel_scope
            task_state.cancel_scope = self
            if self._parent_scope is not None:
                # If using an eager task factory, the parent scope may not even contain
                # the host task
                self._parent_scope._child_scopes.add(self)
                self._parent_scope._tasks.discard(host_task)

        self._timeout()
        self._active = True

        # Start cancelling the host task if the scope was cancelled before entering
        if self._cancel_called:
            self._deliver_cancellation(self)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        del exc_tb

        if not self._active:
            raise RuntimeError("This cancel scope is not active")
        if current_task() is not self._host_task:
            raise RuntimeError(
                "Attempted to exit cancel scope in a different task than it was "
                "entered in"
            )

        assert self._host_task is not None
        host_task_state = _task_states.get(self._host_task)
        if host_task_state is None or host_task_state.cancel_scope is not self:
            raise RuntimeError(
                "Attempted to exit a cancel scope that isn't the current tasks's "
                "current cancel scope"
            )

        try:
            self._active = False
            if self._timeout_handle:
                self._timeout_handle.cancel()
                self._timeout_handle = None

            self._tasks.remove(self._host_task)
            if self._parent_scope is not None:
                self._parent_scope._child_scopes.remove(self)
                self._parent_scope._tasks.add(self._host_task)

            host_task_state.cancel_scope = self._parent_scope

            # Restart the cancellation effort in the closest visible, cancelled parent
            # scope if necessary
            self._restart_cancellation_in_parent()

            # We only swallow the exception iff it was an AnyIO CancelledError, either
            # directly as exc_val or inside an exception group and there are no cancelled
            # parent cancel scopes visible to us here
            if self._cancel_called and not self._parent_cancellation_is_visible_to_us:
                # For each level-cancel() call made on the host task, call uncancel()
                while self._pending_uncancellations:
                    self._host_task.uncancel()
                    self._pending_uncancellations -= 1

                # Update cancelled_caught and check for exceptions we must not swallow
                cannot_swallow_exc_val = False
                if exc_val is not None:
                    for exc in iterate_exceptions(exc_val):
                        if isinstance(exc, CancelledError) and is_anyio_cancellation(
                            exc
                        ):
                            self._cancelled_caught = True
                        else:
                            cannot_swallow_exc_val = True

                return self._cancelled_caught and not cannot_swallow_exc_val
            else:
                if self._pending_uncancellations:
                    assert self._parent_scope is not None
                    assert self._parent_scope._pending_uncancellations is not None
                    self._parent_scope._pending_uncancellations += (
                        self._pending_uncancellations
                    )
                    self._pending_uncancellations = 0

                return False
        finally:
            self._host_task = None
            del exc_val

    @property
    def _effectively_cancelled(self) -> bool:
        cancel_scope: CancelScope | None = self
        while cancel_scope is not None:
            if cancel_scope._cancel_called:
                return True

            if cancel_scope.shield:
                return False

            cancel_scope = cancel_scope._parent_scope

        return False

    @property
    def _parent_cancellation_is_visible_to_us(self) -> bool:
        return (
            self._parent_scope is not None
            and not self.shield
            and self._parent_scope._effectively_cancelled
        )

    def _timeout(self) -> None:
        if self._deadline != math.inf:
            loop = get_running_loop()
            if loop.time() >= self._deadline:
                self.cancel()
            else:
                self._timeout_handle = loop.call_at(self._deadline, self._timeout)

    def _deliver_cancellation(self, origin: CancelScope) -> bool:
        """
        Deliver cancellation to directly contained tasks and nested cancel scopes.

        Schedule another run at the end if we still have tasks eligible for
        cancellation.

        :param origin: the cancel scope that originated the cancellation
        :return: ``True`` if the delivery needs to be retried on the next cycle

        """
        should_retry = False
        current = current_task()
        for task in self._tasks:
            should_retry = True
            if task._must_cancel:  # type: ignore[attr-defined]
                continue

            # The task is eligible for cancellation if it has started
            if task is not current and (task is self._host_task or _task_started(task)):
                waiter = task._fut_waiter  # type: ignore[attr-defined]
                if not isinstance(waiter, asyncio.Future) or not waiter.done():
                    task.cancel(f"Cancelled by cancel scope {id(origin):x}")
                    if (
                        task is origin._host_task
                        and origin._pending_uncancellations is not None
                    ):
                        origin._pending_uncancellations += 1

        # Deliver cancellation to child scopes that aren't shielded or running their own
        # cancellation callbacks
        for scope in self._child_scopes:
            if not scope._shield and not scope.cancel_called:
                should_retry = scope._deliver_cancellation(origin) or should_retry

        # Schedule another callback if there are still tasks left
        if origin is self:
            if should_retry:
                self._cancel_handle = get_running_loop().call_soon(
                    self._deliver_cancellation, origin
                )
            else:
                self._cancel_handle = None

        return should_retry

    def _restart_cancellation_in_parent(self) -> None:
        """
        Restart the cancellation effort in the closest directly cancelled parent scope.

        """
        scope = self._parent_scope
        while scope is not None:
            if scope._cancel_called:
                if scope._cancel_handle is None:
                    scope._deliver_cancellation(scope)

                break

            # No point in looking beyond any shielded scope
            if scope._shield:
                break

            scope = scope._parent_scope

    def cancel(self) -> None:
        if not self._cancel_called:
            if self._timeout_handle:
                self._timeout_handle.cancel()
                self._timeout_handle = None

            self._cancel_called = True
            if self._host_task is not None:
                self._deliver_cancellation(self)

    @property
    def deadline(self) -> float:
        return self._deadline

    @deadline.setter
    def deadline(self, value: float) -> None:
        self._deadline = float(value)
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
            self._timeout_handle = None

        if self._active and not self._cancel_called:
            self._timeout()

    @property
    def cancel_called(self) -> bool:
        return self._cancel_called

    @property
    def cancelled_caught(self) -> bool:
        return self._cancelled_caught

    @property
    def shield(self) -> bool:
        return self._shield

    @shield.setter
    def shield(self, value: bool) -> None:
        if self._shield != value:
            self._shield = value
            if not value:
                self._restart_cancellation_in_parent()


#
# Task states
#


class TaskState:
    """
    Encapsulates auxiliary task information that cannot be added to the Task instance
    itself because there are no guarantees about its implementation.
    """

    __slots__ = "parent_id", "cancel_scope", "__weakref__"

    def __init__(self, parent_id: int | None, cancel_scope: CancelScope | None):
        self.parent_id = parent_id
        self.cancel_scope = cancel_scope


_task_states: WeakKeyDictionary[asyncio.Task, TaskState] = WeakKeyDictionary()


#
# Task groups
#


class _AsyncioTaskStatus(abc.TaskStatus):
    def __init__(self, future: asyncio.Future, parent_id: int):
        self._future = future
        self._parent_id = parent_id

    def started(self, value: T_contra | None = None) -> None:
        try:
            self._future.set_result(value)
        except asyncio.InvalidStateError:
            if not self._future.cancelled():
                raise RuntimeError(
                    "called 'started' twice on the same task status"
                ) from None

        task = cast(asyncio.Task, current_task())
        _task_states[task].parent_id = self._parent_id


if sys.version_info >= (3, 12):
    _eager_task_factory_code: CodeType | None = asyncio.eager_task_factory.__code__
else:
    _eager_task_factory_code = None


class TaskGroup(abc.TaskGroup):
    def __init__(self) -> None:
        self.cancel_scope: CancelScope = CancelScope()
        self._active = False
        self._exceptions: list[BaseException] = []
        self._tasks: set[asyncio.Task] = set()
        self._on_completed_fut: asyncio.Future[None] | None = None

    async def __aenter__(self) -> TaskGroup:
        self.cancel_scope.__enter__()
        self._active = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        try:
            if exc_val is not None:
                self.cancel_scope.cancel()
                if not isinstance(exc_val, CancelledError):
                    self._exceptions.append(exc_val)

            loop = get_running_loop()
            try:
                if self._tasks:
                    with CancelScope() as wait_scope:
                        while self._tasks:
                            self._on_completed_fut = loop.create_future()

                            try:
                                await self._on_completed_fut
                            except CancelledError as exc:
                                # Shield the scope against further cancellation attempts,
                                # as they're not productive (#695)
                                wait_scope.shield = True
                                self.cancel_scope.cancel()

                                # Set exc_val from the cancellation exception if it was
                                # previously unset. However, we should not replace a native
                                # cancellation exception with one raise by a cancel scope.
                                if exc_val is None or (
                                    isinstance(exc_val, CancelledError)
                                    and not is_anyio_cancellation(exc)
                                ):
                                    exc_val = exc

                            self._on_completed_fut = None
                else:
                    # If there are no child tasks to wait on, run at least one checkpoint
                    # anyway
                    await AsyncIOBackend.cancel_shielded_checkpoint()

                self._active = False
                if self._exceptions:
                    # The exception that got us here should already have been
                    # added to self._exceptions so it's ok to break exception
                    # chaining and avoid adding a "During handling of above..."
                    # for each nesting level.
                    raise BaseExceptionGroup(
                        "unhandled errors in a TaskGroup", self._exceptions
                    ) from None
                elif exc_val:
                    raise exc_val
            except BaseException as exc:
                if self.cancel_scope.__exit__(type(exc), exc, exc.__traceback__):
                    return True

                raise

            return self.cancel_scope.__exit__(exc_type, exc_val, exc_tb)
        finally:
            del exc_val, exc_tb, self._exceptions

    def _spawn(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[Any]],
        args: tuple[Unpack[PosArgsT]],
        name: object,
        task_status_future: asyncio.Future | None = None,
    ) -> asyncio.Task:
        def task_done(_task: asyncio.Task) -> None:
            task_state = _task_states[_task]
            assert task_state.cancel_scope is not None
            assert _task in task_state.cancel_scope._tasks
            task_state.cancel_scope._tasks.remove(_task)
            self._tasks.remove(task)
            del _task_states[_task]

            if self._on_completed_fut is not None and not self._tasks:
                try:
                    self._on_completed_fut.set_result(None)
                except asyncio.InvalidStateError:
                    pass

            try:
                exc = _task.exception()
            except CancelledError as e:
                while isinstance(e.__context__, CancelledError):
                    e = e.__context__

                exc = e

            if exc is not None:
                # The future can only be in the cancelled state if the host task was
                # cancelled, so return immediately instead of adding one more
                # CancelledError to the exceptions list
                if task_status_future is not None and task_status_future.cancelled():
                    return

                if task_status_future is None or task_status_future.done():
                    if not isinstance(exc, CancelledError):
                        self._exceptions.append(exc)

                    if not self.cancel_scope._effectively_cancelled:
                        self.cancel_scope.cancel()
                else:
                    task_status_future.set_exception(exc)
            elif task_status_future is not None and not task_status_future.done():
                task_status_future.set_exception(
                    RuntimeError("Child exited without calling task_status.started()")
                )

        if not self._active:
            raise RuntimeError(
                "This task group is not active; no new tasks can be started."
            )

        kwargs = {}
        if task_status_future:
            parent_id = id(current_task())
            kwargs["task_status"] = _AsyncioTaskStatus(
                task_status_future, id(self.cancel_scope._host_task)
            )
        else:
            parent_id = id(self.cancel_scope._host_task)

        coro = func(*args, **kwargs)
        if not iscoroutine(coro):
            prefix = f"{func.__module__}." if hasattr(func, "__module__") else ""
            raise TypeError(
                f"Expected {prefix}{func.__qualname__}() to return a coroutine, but "
                f"the return value ({coro!r}) is not a coroutine object"
            )

        name = get_callable_name(func) if name is None else str(name)
        loop = asyncio.get_running_loop()
        if (
            (factory := loop.get_task_factory())
            and getattr(factory, "__code__", None) is _eager_task_factory_code
            and (closure := getattr(factory, "__closure__", None))
        ):
            custom_task_constructor = closure[0].cell_contents
            task = custom_task_constructor(coro, loop=loop, name=name)
        else:
            task = create_task(coro, name=name)

        # Make the spawned task inherit the task group's cancel scope
        _task_states[task] = TaskState(
            parent_id=parent_id, cancel_scope=self.cancel_scope
        )
        self.cancel_scope._tasks.add(task)
        self._tasks.add(task)
        task.add_done_callback(task_done)
        return task

    def start_soon(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[Any]],
        *args: Unpack[PosArgsT],
        name: object = None,
    ) -> None:
        self._spawn(func, args, name)

    async def start(
        self, func: Callable[..., Awaitable[Any]], *args: object, name: object = None
    ) -> Any:
        future: asyncio.Future = asyncio.Future()
        task = self._spawn(func, args, name, future)

        # If the task raises an exception after sending a start value without a switch
        # point between, the task group is cancelled and this method never proceeds to
        # process the completed future. That's why we have to have a shielded cancel
        # scope here.
        try:
            return await future
        except CancelledError:
            # Cancel the task and wait for it to exit before returning
            task.cancel()
            with CancelScope(shield=True), suppress(CancelledError):
                await task

            raise


#
# Threads
#

_Retval_Queue_Type = tuple[Optional[T_Retval], Optional[BaseException]]


class WorkerThread(Thread):
    MAX_IDLE_TIME = 10  # seconds

    def __init__(
        self,
        root_task: asyncio.Task,
        workers: set[WorkerThread],
        idle_workers: deque[WorkerThread],
    ):
        super().__init__(name="AnyIO worker thread")
        self.root_task = root_task
        self.workers = workers
        self.idle_workers = idle_workers
        self.loop = root_task._loop
        self.queue: Queue[
            tuple[Context, Callable, tuple, asyncio.Future, CancelScope] | None
        ] = Queue(2)
        self.idle_since = AsyncIOBackend.current_time()
        self.stopping = False

    def _report_result(
        self, future: asyncio.Future, result: Any, exc: BaseException | None
    ) -> None:
        self.idle_since = AsyncIOBackend.current_time()
        if not self.stopping:
            self.idle_workers.append(self)

        if not future.cancelled():
            if exc is not None:
                if isinstance(exc, StopIteration):
                    new_exc = RuntimeError("coroutine raised StopIteration")
                    new_exc.__cause__ = exc
                    exc = new_exc

                future.set_exception(exc)
            else:
                future.set_result(result)

    def run(self) -> None:
        with claim_worker_thread(AsyncIOBackend, self.loop):
            while True:
                item = self.queue.get()
                if item is None:
                    # Shutdown command received
                    return

                context, func, args, future, cancel_scope = item
                if not future.cancelled():
                    result = None
                    exception: BaseException | None = None
                    threadlocals.current_cancel_scope = cancel_scope
                    try:
                        result = context.run(func, *args)
                    except BaseException as exc:
                        exception = exc
                    finally:
                        del threadlocals.current_cancel_scope

                    if not self.loop.is_closed():
                        self.loop.call_soon_threadsafe(
                            self._report_result, future, result, exception
                        )

                    del result, exception

                self.queue.task_done()
                del item, context, func, args, future, cancel_scope

    def stop(self, f: asyncio.Task | None = None) -> None:
        self.stopping = True
        self.queue.put_nowait(None)
        self.workers.discard(self)
        try:
            self.idle_workers.remove(self)
        except ValueError:
            pass


_threadpool_idle_workers: RunVar[deque[WorkerThread]] = RunVar(
    "_threadpool_idle_workers"
)
_threadpool_workers: RunVar[set[WorkerThread]] = RunVar("_threadpool_workers")


class BlockingPortal(abc.BlockingPortal):
    def __new__(cls) -> BlockingPortal:
        return object.__new__(cls)

    def __init__(self) -> None:
        super().__init__()
        self._loop = get_running_loop()

    def _spawn_task_from_thread(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        name: object,
        future: Future[T_Retval],
    ) -> None:
        AsyncIOBackend.run_sync_from_thread(
            partial(self._task_group.start_soon, name=name),
            (self._call_func, func, args, kwargs, future),
            self._loop,
        )


#
# Subprocesses
#


@dataclass(eq=False)
class StreamReaderWrapper(abc.ByteReceiveStream):
    _stream: asyncio.StreamReader

    async def receive(self, max_bytes: int = 65536) -> bytes:
        data = await self._stream.read(max_bytes)
        if data:
            return data
        else:
            raise EndOfStream

    async def aclose(self) -> None:
        self._stream.set_exception(ClosedResourceError())
        await AsyncIOBackend.checkpoint()


@dataclass(eq=False)
class StreamWriterWrapper(abc.ByteSendStream):
    _stream: asyncio.StreamWriter

    async def send(self, item: bytes) -> None:
        self._stream.write(item)
        await self._stream.drain()

    async def aclose(self) -> None:
        self._stream.close()
        await AsyncIOBackend.checkpoint()


@dataclass(eq=False)
class Process(abc.Process):
    _process: asyncio.subprocess.Process
    _stdin: StreamWriterWrapper | None
    _stdout: StreamReaderWrapper | None
    _stderr: StreamReaderWrapper | None

    async def aclose(self) -> None:
        with CancelScope(shield=True) as scope:
            if self._stdin:
                await self._stdin.aclose()
            if self._stdout:
                await self._stdout.aclose()
            if self._stderr:
                await self._stderr.aclose()

            scope.shield = False
            try:
                await self.wait()
            except BaseException:
                scope.shield = True
                self.kill()
                await self.wait()
                raise

    async def wait(self) -> int:
        return await self._process.wait()

    def terminate(self) -> None:
        self._process.terminate()

    def kill(self) -> None:
        self._process.kill()

    def send_signal(self, signal: int) -> None:
        self._process.send_signal(signal)

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        return self._process.returncode

    @property
    def stdin(self) -> abc.ByteSendStream | None:
        return self._stdin

    @property
    def stdout(self) -> abc.ByteReceiveStream | None:
        return self._stdout

    @property
    def stderr(self) -> abc.ByteReceiveStream | None:
        return self._stderr


def _forcibly_shutdown_process_pool_on_exit(
    workers: set[Process], _task: object
) -> None:
    """
    Forcibly shuts down worker processes belonging to this event loop."""
    child_watcher: asyncio.AbstractChildWatcher | None = None
    if sys.version_info < (3, 12):
        try:
            child_watcher = asyncio.get_event_loop_policy().get_child_watcher()
        except NotImplementedError:
            pass

    # Close as much as possible (w/o async/await) to avoid warnings
    for process in workers:
        if process.returncode is None:
            continue

        process._stdin._stream._transport.close()  # type: ignore[union-attr]
        process._stdout._stream._transport.close()  # type: ignore[union-attr]
        process._stderr._stream._transport.close()  # type: ignore[union-attr]
        process.kill()
        if child_watcher:
            child_watcher.remove_child_handler(process.pid)


async def _shutdown_process_pool_on_exit(workers: set[abc.Process]) -> None:
    """
    Shuts down worker processes belonging to this event loop.

    NOTE: this only works when the event loop was started using asyncio.run() or
    anyio.run().

    """
    process: abc.Process
    try:
        await sleep(math.inf)
    except asyncio.CancelledError:
        for process in workers:
            if process.returncode is None:
                process.kill()

        for process in workers:
            await process.aclose()


#
# Sockets and networking
#


class StreamProtocol(asyncio.Protocol):
    read_queue: deque[bytes]
    read_event: asyncio.Event
    write_event: asyncio.Event
    exception: Exception | None = None
    is_at_eof: bool = False

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.read_queue = deque()
        self.read_event = asyncio.Event()
        self.write_event = asyncio.Event()
        self.write_event.set()
        cast(asyncio.Transport, transport).set_write_buffer_limits(0)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            self.exception = BrokenResourceError()
            self.exception.__cause__ = exc

        self.read_event.set()
        self.write_event.set()

    def data_received(self, data: bytes) -> None:
        # ProactorEventloop sometimes sends bytearray instead of bytes
        self.read_queue.append(bytes(data))
        self.read_event.set()

    def eof_received(self) -> bool | None:
        self.is_at_eof = True
        self.read_event.set()
        return True

    def pause_writing(self) -> None:
        self.write_event = asyncio.Event()

    def resume_writing(self) -> None:
        self.write_event.set()


class DatagramProtocol(asyncio.DatagramProtocol):
    read_queue: deque[tuple[bytes, IPSockAddrType]]
    read_event: asyncio.Event
    write_event: asyncio.Event
    exception: Exception | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.read_queue = deque(maxlen=100)  # arbitrary value
        self.read_event = asyncio.Event()
        self.write_event = asyncio.Event()
        self.write_event.set()

    def connection_lost(self, exc: Exception | None) -> None:
        self.read_event.set()
        self.write_event.set()

    def datagram_received(self, data: bytes, addr: IPSockAddrType) -> None:
        addr = convert_ipv6_sockaddr(addr)
        self.read_queue.append((data, addr))
        self.read_event.set()

    def error_received(self, exc: Exception) -> None:
        self.exception = exc

    def pause_writing(self) -> None:
        self.write_event.clear()

    def resume_writing(self) -> None:
        self.write_event.set()


class SocketStream(abc.SocketStream):
    def __init__(self, transport: asyncio.Transport, protocol: StreamProtocol):
        self._transport = transport
        self._protocol = protocol
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")
        self._closed = False

    @property
    def _raw_socket(self) -> socket.socket:
        return self._transport.get_extra_info("socket")

    async def receive(self, max_bytes: int = 65536) -> bytes:
        with self._receive_guard:
            if (
                not self._protocol.read_event.is_set()
                and not self._transport.is_closing()
                and not self._protocol.is_at_eof
            ):
                self._transport.resume_reading()
                await self._protocol.read_event.wait()
                self._transport.pause_reading()
            else:
                await AsyncIOBackend.checkpoint()

            try:
                chunk = self._protocol.read_queue.popleft()
            except IndexError:
                if self._closed:
                    raise ClosedResourceError from None
                elif self._protocol.exception:
                    raise self._protocol.exception from None
                else:
                    raise EndOfStream from None

            if len(chunk) > max_bytes:
                # Split the oversized chunk
                chunk, leftover = chunk[:max_bytes], chunk[max_bytes:]
                self._protocol.read_queue.appendleft(leftover)

            # If the read queue is empty, clear the flag so that the next call will
            # block until data is available
            if not self._protocol.read_queue:
                self._protocol.read_event.clear()

        return chunk

    async def send(self, item: bytes) -> None:
        with self._send_guard:
            await AsyncIOBackend.checkpoint()

            if self._closed:
                raise ClosedResourceError
            elif self._protocol.exception is not None:
                raise self._protocol.exception

            try:
                self._transport.write(item)
            except RuntimeError as exc:
                if self._transport.is_closing():
                    raise BrokenResourceError from exc
                else:
                    raise

            await self._protocol.write_event.wait()

    async def send_eof(self) -> None:
        try:
            self._transport.write_eof()
        except OSError:
            pass

    async def aclose(self) -> None:
        if not self._transport.is_closing():
            self._closed = True
            try:
                self._transport.write_eof()
            except OSError:
                pass

            self._transport.close()
            await sleep(0)
            self._transport.abort()


class _RawSocketMixin:
    _receive_future: asyncio.Future | None = None
    _send_future: asyncio.Future | None = None
    _closing = False

    def __init__(self, raw_socket: socket.socket):
        self.__raw_socket = raw_socket
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")

    @property
    def _raw_socket(self) -> socket.socket:
        return self.__raw_socket

    def _wait_until_readable(self, loop: asyncio.AbstractEventLoop) -> asyncio.Future:
        def callback(f: object) -> None:
            del self._receive_future
            loop.remove_reader(self.__raw_socket)

        f = self._receive_future = asyncio.Future()
        loop.add_reader(self.__raw_socket, f.set_result, None)
        f.add_done_callback(callback)
        return f

    def _wait_until_writable(self, loop: asyncio.AbstractEventLoop) -> asyncio.Future:
        def callback(f: object) -> None:
            del self._send_future
            loop.remove_writer(self.__raw_socket)

        f = self._send_future = asyncio.Future()
        loop.add_writer(self.__raw_socket, f.set_result, None)
        f.add_done_callback(callback)
        return f

    async def aclose(self) -> None:
        if not self._closing:
            self._closing = True
            if self.__raw_socket.fileno() != -1:
                self.__raw_socket.close()

            if self._receive_future:
                self._receive_future.set_result(None)
            if self._send_future:
                self._send_future.set_result(None)


class UNIXSocketStream(_RawSocketMixin, abc.UNIXSocketStream):
    async def send_eof(self) -> None:
        with self._send_guard:
            self._raw_socket.shutdown(socket.SHUT_WR)

    async def receive(self, max_bytes: int = 65536) -> bytes:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._receive_guard:
            while True:
                try:
                    data = self._raw_socket.recv(max_bytes)
                except BlockingIOError:
                    await self._wait_until_readable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    if not data:
                        raise EndOfStream

                    return data

    async def send(self, item: bytes) -> None:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._send_guard:
            view = memoryview(item)
            while view:
                try:
                    bytes_sent = self._raw_socket.send(view)
                except BlockingIOError:
                    await self._wait_until_writable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    view = view[bytes_sent:]

    async def receive_fds(self, msglen: int, maxfds: int) -> tuple[bytes, list[int]]:
        if not isinstance(msglen, int) or msglen < 0:
            raise ValueError("msglen must be a non-negative integer")
        if not isinstance(maxfds, int) or maxfds < 1:
            raise ValueError("maxfds must be a positive integer")

        loop = get_running_loop()
        fds = array.array("i")
        await AsyncIOBackend.checkpoint()
        with self._receive_guard:
            while True:
                try:
                    message, ancdata, flags, addr = self._raw_socket.recvmsg(
                        msglen, socket.CMSG_LEN(maxfds * fds.itemsize)
                    )
                except BlockingIOError:
                    await self._wait_until_readable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    if not message and not ancdata:
                        raise EndOfStream

                    break

        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level != socket.SOL_SOCKET or cmsg_type != socket.SCM_RIGHTS:
                raise RuntimeError(
                    f"Received unexpected ancillary data; message = {message!r}, "
                    f"cmsg_level = {cmsg_level}, cmsg_type = {cmsg_type}"
                )

            fds.frombytes(cmsg_data[: len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])

        return message, list(fds)

    async def send_fds(self, message: bytes, fds: Collection[int | IOBase]) -> None:
        if not message:
            raise ValueError("message must not be empty")
        if not fds:
            raise ValueError("fds must not be empty")

        loop = get_running_loop()
        filenos: list[int] = []
        for fd in fds:
            if isinstance(fd, int):
                filenos.append(fd)
            elif isinstance(fd, IOBase):
                filenos.append(fd.fileno())

        fdarray = array.array("i", filenos)
        await AsyncIOBackend.checkpoint()
        with self._send_guard:
            while True:
                try:
                    # The ignore can be removed after mypy picks up
                    # https://github.com/python/typeshed/pull/5545
                    self._raw_socket.sendmsg(
                        [message], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fdarray)]
                    )
                    break
                except BlockingIOError:
                    await self._wait_until_writable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc


class TCPSocketListener(abc.SocketListener):
    _accept_scope: CancelScope | None = None
    _closed = False

    def __init__(self, raw_socket: socket.socket):
        self.__raw_socket = raw_socket
        self._loop = cast(asyncio.BaseEventLoop, get_running_loop())
        self._accept_guard = ResourceGuard("accepting connections from")

    @property
    def _raw_socket(self) -> socket.socket:
        return self.__raw_socket

    async def accept(self) -> abc.SocketStream:
        if self._closed:
            raise ClosedResourceError

        with self._accept_guard:
            await AsyncIOBackend.checkpoint()
            with CancelScope() as self._accept_scope:
                try:
                    client_sock, _addr = await self._loop.sock_accept(self._raw_socket)
                except asyncio.CancelledError:
                    # Workaround for https://bugs.python.org/issue41317
                    try:
                        self._loop.remove_reader(self._raw_socket)
                    except (ValueError, NotImplementedError):
                        pass

                    if self._closed:
                        raise ClosedResourceError from None

                    raise
                finally:
                    self._accept_scope = None

        client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        transport, protocol = await self._loop.connect_accepted_socket(
            StreamProtocol, client_sock
        )
        return SocketStream(transport, protocol)

    async def aclose(self) -> None:
        if self._closed:
            return

        self._closed = True
        if self._accept_scope:
            # Workaround for https://bugs.python.org/issue41317
            try:
                self._loop.remove_reader(self._raw_socket)
            except (ValueError, NotImplementedError):
                pass

            self._accept_scope.cancel()
            await sleep(0)

        self._raw_socket.close()


class UNIXSocketListener(abc.SocketListener):
    def __init__(self, raw_socket: socket.socket):
        self.__raw_socket = raw_socket
        self._loop = get_running_loop()
        self._accept_guard = ResourceGuard("accepting connections from")
        self._closed = False

    async def accept(self) -> abc.SocketStream:
        await AsyncIOBackend.checkpoint()
        with self._accept_guard:
            while True:
                try:
                    client_sock, _ = self.__raw_socket.accept()
                    client_sock.setblocking(False)
                    return UNIXSocketStream(client_sock)
                except BlockingIOError:
                    f: asyncio.Future = asyncio.Future()
                    self._loop.add_reader(self.__raw_socket, f.set_result, None)
                    f.add_done_callback(
                        lambda _: self._loop.remove_reader(self.__raw_socket)
                    )
                    await f
                except OSError as exc:
                    if self._closed:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc

    async def aclose(self) -> None:
        self._closed = True
        self.__raw_socket.close()

    @property
    def _raw_socket(self) -> socket.socket:
        return self.__raw_socket


class UDPSocket(abc.UDPSocket):
    def __init__(
        self, transport: asyncio.DatagramTransport, protocol: DatagramProtocol
    ):
        self._transport = transport
        self._protocol = protocol
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")
        self._closed = False

    @property
    def _raw_socket(self) -> socket.socket:
        return self._transport.get_extra_info("socket")

    async def aclose(self) -> None:
        if not self._transport.is_closing():
            self._closed = True
            self._transport.close()

    async def receive(self) -> tuple[bytes, IPSockAddrType]:
        with self._receive_guard:
            await AsyncIOBackend.checkpoint()

            # If the buffer is empty, ask for more data
            if not self._protocol.read_queue and not self._transport.is_closing():
                self._protocol.read_event.clear()
                await self._protocol.read_event.wait()

            try:
                return self._protocol.read_queue.popleft()
            except IndexError:
                if self._closed:
                    raise ClosedResourceError from None
                else:
                    raise BrokenResourceError from None

    async def send(self, item: UDPPacketType) -> None:
        with self._send_guard:
            await AsyncIOBackend.checkpoint()
            await self._protocol.write_event.wait()
            if self._closed:
                raise ClosedResourceError
            elif self._transport.is_closing():
                raise BrokenResourceError
            else:
                self._transport.sendto(*item)


class ConnectedUDPSocket(abc.ConnectedUDPSocket):
    def __init__(
        self, transport: asyncio.DatagramTransport, protocol: DatagramProtocol
    ):
        self._transport = transport
        self._protocol = protocol
        self._receive_guard = ResourceGuard("reading from")
        self._send_guard = ResourceGuard("writing to")
        self._closed = False

    @property
    def _raw_socket(self) -> socket.socket:
        return self._transport.get_extra_info("socket")

    async def aclose(self) -> None:
        if not self._transport.is_closing():
            self._closed = True
            self._transport.close()

    async def receive(self) -> bytes:
        with self._receive_guard:
            await AsyncIOBackend.checkpoint()

            # If the buffer is empty, ask for more data
            if not self._protocol.read_queue and not self._transport.is_closing():
                self._protocol.read_event.clear()
                await self._protocol.read_event.wait()

            try:
                packet = self._protocol.read_queue.popleft()
            except IndexError:
                if self._closed:
                    raise ClosedResourceError from None
                else:
                    raise BrokenResourceError from None

            return packet[0]

    async def send(self, item: bytes) -> None:
        with self._send_guard:
            await AsyncIOBackend.checkpoint()
            await self._protocol.write_event.wait()
            if self._closed:
                raise ClosedResourceError
            elif self._transport.is_closing():
                raise BrokenResourceError
            else:
                self._transport.sendto(item)


class UNIXDatagramSocket(_RawSocketMixin, abc.UNIXDatagramSocket):
    async def receive(self) -> UNIXDatagramPacketType:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._receive_guard:
            while True:
                try:
                    data = self._raw_socket.recvfrom(65536)
                except BlockingIOError:
                    await self._wait_until_readable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    return data

    async def send(self, item: UNIXDatagramPacketType) -> None:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._send_guard:
            while True:
                try:
                    self._raw_socket.sendto(*item)
                except BlockingIOError:
                    await self._wait_until_writable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    return


class ConnectedUNIXDatagramSocket(_RawSocketMixin, abc.ConnectedUNIXDatagramSocket):
    async def receive(self) -> bytes:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._receive_guard:
            while True:
                try:
                    data = self._raw_socket.recv(65536)
                except BlockingIOError:
                    await self._wait_until_readable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    return data

    async def send(self, item: bytes) -> None:
        loop = get_running_loop()
        await AsyncIOBackend.checkpoint()
        with self._send_guard:
            while True:
                try:
                    self._raw_socket.send(item)
                except BlockingIOError:
                    await self._wait_until_writable(loop)
                except OSError as exc:
                    if self._closing:
                        raise ClosedResourceError from None
                    else:
                        raise BrokenResourceError from exc
                else:
                    return


_read_events: RunVar[dict[int, asyncio.Event]] = RunVar("read_events")
_write_events: RunVar[dict[int, asyncio.Event]] = RunVar("write_events")


#
# Synchronization
#


class Event(BaseEvent):
    def __new__(cls) -> Event:
        return object.__new__(cls)

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    async def wait(self) -> None:
        if self.is_set():
            await AsyncIOBackend.checkpoint()
        else:
            await self._event.wait()

    def statistics(self) -> EventStatistics:
        return EventStatistics(len(self._event._waiters))


class Lock(BaseLock):
    def __new__(cls, *, fast_acquire: bool = False) -> Lock:
        return object.__new__(cls)

    def __init__(self, *, fast_acquire: bool = False) -> None:
        self._fast_acquire = fast_acquire
        self._owner_task: asyncio.Task | None = None
        self._waiters: deque[tuple[asyncio.Task, asyncio.Future]] = deque()

    async def acquire(self) -> None:
        task = cast(asyncio.Task, current_task())
        if self._owner_task is None and not self._waiters:
            await AsyncIOBackend.checkpoint_if_cancelled()
            self._owner_task = task

            # Unless on the "fast path", yield control of the event loop so that other
            # tasks can run too
            if not self._fast_acquire:
                try:
                    await AsyncIOBackend.cancel_shielded_checkpoint()
                except CancelledError:
                    self.release()
                    raise

            return

        if self._owner_task == task:
            raise RuntimeError("Attempted to acquire an already held Lock")

        fut: asyncio.Future[None] = asyncio.Future()
        item = task, fut
        self._waiters.append(item)
        try:
            await fut
        except CancelledError:
            self._waiters.remove(item)
            if self._owner_task is task:
                self.release()

            raise

        self._waiters.remove(item)

    def acquire_nowait(self) -> None:
        task = cast(asyncio.Task, current_task())
        if self._owner_task is None and not self._waiters:
            self._owner_task = task
            return

        if self._owner_task is task:
            raise RuntimeError("Attempted to acquire an already held Lock")

        raise WouldBlock

    def locked(self) -> bool:
        return self._owner_task is not None

    def release(self) -> None:
        if self._owner_task != current_task():
            raise RuntimeError("The current task is not holding this lock")

        for task, fut in self._waiters:
            if not fut.cancelled():
                self._owner_task = task
                fut.set_result(None)
                return

        self._owner_task = None

    def statistics(self) -> LockStatistics:
        task_info = AsyncIOTaskInfo(self._owner_task) if self._owner_task else None
        return LockStatistics(self.locked(), task_info, len(self._waiters))


class Semaphore(BaseSemaphore):
    def __new__(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> Semaphore:
        return object.__new__(cls)

    def __init__(
        self,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ):
        super().__init__(initial_value, max_value=max_value)
        self._value = initial_value
        self._max_value = max_value
        self._fast_acquire = fast_acquire
        self._waiters: deque[asyncio.Future[None]] = deque()

    async def acquire(self) -> None:
        if self._value > 0 and not self._waiters:
            await AsyncIOBackend.checkpoint_if_cancelled()
            self._value -= 1

            # Unless on the "fast path", yield control of the event loop so that other
            # tasks can run too
            if not self._fast_acquire:
                try:
                    await AsyncIOBackend.cancel_shielded_checkpoint()
                except CancelledError:
                    self.release()
                    raise

            return

        fut: asyncio.Future[None] = asyncio.Future()
        self._waiters.append(fut)
        try:
            await fut
        except CancelledError:
            try:
                self._waiters.remove(fut)
            except ValueError:
                self.release()

            raise

    def acquire_nowait(self) -> None:
        if self._value == 0:
            raise WouldBlock

        self._value -= 1

    def release(self) -> None:
        if self._max_value is not None and self._value == self._max_value:
            raise ValueError("semaphore released too many times")

        for fut in self._waiters:
            if not fut.cancelled():
                fut.set_result(None)
                self._waiters.remove(fut)
                return

        self._value += 1

    @property
    def value(self) -> int:
        return self._value

    @property
    def max_value(self) -> int | None:
        return self._max_value

    def statistics(self) -> SemaphoreStatistics:
        return SemaphoreStatistics(len(self._waiters))


class CapacityLimiter(BaseCapacityLimiter):
    _total_tokens: float = 0

    def __new__(cls, total_tokens: float) -> CapacityLimiter:
        return object.__new__(cls)

    def __init__(self, total_tokens: float):
        self._borrowers: set[Any] = set()
        self._wait_queue: OrderedDict[Any, asyncio.Event] = OrderedDict()
        self.total_tokens = total_tokens

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    @property
    def total_tokens(self) -> float:
        return self._total_tokens

    @total_tokens.setter
    def total_tokens(self, value: float) -> None:
        if not isinstance(value, int) and not math.isinf(value):
            raise TypeError("total_tokens must be an int or math.inf")
        if value < 1:
            raise ValueError("total_tokens must be >= 1")

        waiters_to_notify = max(value - self._total_tokens, 0)
        self._total_tokens = value

        # Notify waiting tasks that they have acquired the limiter
        while self._wait_queue and waiters_to_notify:
            event = self._wait_queue.popitem(last=False)[1]
            event.set()
            waiters_to_notify -= 1

    @property
    def borrowed_tokens(self) -> int:
        return len(self._borrowers)

    @property
    def available_tokens(self) -> float:
        return self._total_tokens - len(self._borrowers)

    def acquire_nowait(self) -> None:
        self.acquire_on_behalf_of_nowait(current_task())

    def acquire_on_behalf_of_nowait(self, borrower: object) -> None:
        if borrower in self._borrowers:
            raise RuntimeError(
                "this borrower is already holding one of this CapacityLimiter's tokens"
            )

        if self._wait_queue or len(self._borrowers) >= self._total_tokens:
            raise WouldBlock

        self._borrowers.add(borrower)

    async def acquire(self) -> None:
        return await self.acquire_on_behalf_of(current_task())

    async def acquire_on_behalf_of(self, borrower: object) -> None:
        await AsyncIOBackend.checkpoint_if_cancelled()
        try:
            self.acquire_on_behalf_of_nowait(borrower)
        except WouldBlock:
            event = asyncio.Event()
            self._wait_queue[borrower] = event
            try:
                await event.wait()
            except BaseException:
                self._wait_queue.pop(borrower, None)
                raise

            self._borrowers.add(borrower)
        else:
            try:
                await AsyncIOBackend.cancel_shielded_checkpoint()
            except BaseException:
                self.release()
                raise

    def release(self) -> None:
        self.release_on_behalf_of(current_task())

    def release_on_behalf_of(self, borrower: object) -> None:
        try:
            self._borrowers.remove(borrower)
        except KeyError:
            raise RuntimeError(
                "this borrower isn't holding any of this CapacityLimiter's tokens"
            ) from None

        # Notify the next task in line if this limiter has free capacity now
        if self._wait_queue and len(self._borrowers) < self._total_tokens:
            event = self._wait_queue.popitem(last=False)[1]
            event.set()

    def statistics(self) -> CapacityLimiterStatistics:
        return CapacityLimiterStatistics(
            self.borrowed_tokens,
            self.total_tokens,
            tuple(self._borrowers),
            len(self._wait_queue),
        )


_default_thread_limiter: RunVar[CapacityLimiter] = RunVar("_default_thread_limiter")


#
# Operating system signals
#


class _SignalReceiver:
    def __init__(self, signals: tuple[Signals, ...]):
        self._signals = signals
        self._loop = get_running_loop()
        self._signal_queue: deque[Signals] = deque()
        self._future: asyncio.Future = asyncio.Future()
        self._handled_signals: set[Signals] = set()

    def _deliver(self, signum: Signals) -> None:
        self._signal_queue.append(signum)
        if not self._future.done():
            self._future.set_result(None)

    def __enter__(self) -> _SignalReceiver:
        for sig in set(self._signals):
            self._loop.add_signal_handler(sig, self._deliver, sig)
            self._handled_signals.add(sig)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        for sig in self._handled_signals:
            self._loop.remove_signal_handler(sig)

    def __aiter__(self) -> _SignalReceiver:
        return self

    async def __anext__(self) -> Signals:
        await AsyncIOBackend.checkpoint()
        if not self._signal_queue:
            self._future = asyncio.Future()
            await self._future

        return self._signal_queue.popleft()


#
# Testing and debugging
#


class AsyncIOTaskInfo(TaskInfo):
    def __init__(self, task: asyncio.Task):
        task_state = _task_states.get(task)
        if task_state is None:
            parent_id = None
        else:
            parent_id = task_state.parent_id

        coro = task.get_coro()
        assert coro is not None, "created TaskInfo from a completed Task"
        super().__init__(id(task), parent_id, task.get_name(), coro)
        self._task = weakref.ref(task)

    def has_pending_cancellation(self) -> bool:
        if not (task := self._task()):
            # If the task isn't around anymore, it won't have a pending cancellation
            return False

        if task._must_cancel:  # type: ignore[attr-defined]
            return True
        elif (
            isinstance(task._fut_waiter, asyncio.Future)  # type: ignore[attr-defined]
            and task._fut_waiter.cancelled()  # type: ignore[attr-defined]
        ):
            return True

        if task_state := _task_states.get(task):
            if cancel_scope := task_state.cancel_scope:
                return cancel_scope._effectively_cancelled

        return False


class TestRunner(abc.TestRunner):
    _send_stream: MemoryObjectSendStream[tuple[Awaitable[Any], asyncio.Future[Any]]]

    def __init__(
        self,
        *,
        debug: bool | None = None,
        use_uvloop: bool = False,
        loop_factory: Callable[[], AbstractEventLoop] | None = None,
    ) -> None:
        if use_uvloop and loop_factory is None:
            import uvloop

            loop_factory = uvloop.new_event_loop

        self._runner = Runner(debug=debug, loop_factory=loop_factory)
        self._exceptions: list[BaseException] = []
        self._runner_task: asyncio.Task | None = None

    def __enter__(self) -> TestRunner:
        self._runner.__enter__()
        self.get_loop().set_exception_handler(self._exception_handler)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._runner.__exit__(exc_type, exc_val, exc_tb)

    def get_loop(self) -> AbstractEventLoop:
        return self._runner.get_loop()

    def _exception_handler(
        self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        if isinstance(context.get("exception"), Exception):
            self._exceptions.append(context["exception"])
        else:
            loop.default_exception_handler(context)

    def _raise_async_exceptions(self) -> None:
        # Re-raise any exceptions raised in asynchronous callbacks
        if self._exceptions:
            exceptions, self._exceptions = self._exceptions, []
            if len(exceptions) == 1:
                raise exceptions[0]
            elif exceptions:
                raise BaseExceptionGroup(
                    "Multiple exceptions occurred in asynchronous callbacks", exceptions
                )

    async def _run_tests_and_fixtures(
        self,
        receive_stream: MemoryObjectReceiveStream[
            tuple[Awaitable[T_Retval], asyncio.Future[T_Retval]]
        ],
    ) -> None:
        from _pytest.outcomes import OutcomeException

        with receive_stream, self._send_stream:
            async for coro, future in receive_stream:
                try:
                    retval = await coro
                except CancelledError as exc:
                    if not future.cancelled():
                        future.cancel(*exc.args)

                    raise
                except BaseException as exc:
                    if not future.cancelled():
                        future.set_exception(exc)

                    if not isinstance(exc, (Exception, OutcomeException)):
                        raise
                else:
                    if not future.cancelled():
                        future.set_result(retval)

    async def _call_in_runner_task(
        self,
        func: Callable[P, Awaitable[T_Retval]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T_Retval:
        if not self._runner_task:
            self._send_stream, receive_stream = create_memory_object_stream[
                tuple[Awaitable[Any], asyncio.Future]
            ](1)
            self._runner_task = self.get_loop().create_task(
                self._run_tests_and_fixtures(receive_stream)
            )

        coro = func(*args, **kwargs)
        future: asyncio.Future[T_Retval] = self.get_loop().create_future()
        self._send_stream.send_nowait((coro, future))
        return await future

    def run_asyncgen_fixture(
        self,
        fixture_func: Callable[..., AsyncGenerator[T_Retval, Any]],
        kwargs: dict[str, Any],
    ) -> Iterable[T_Retval]:
        asyncgen = fixture_func(**kwargs)
        fixturevalue: T_Retval = self.get_loop().run_until_complete(
            self._call_in_runner_task(asyncgen.asend, None)
        )
        self._raise_async_exceptions()

        yield fixturevalue

        try:
            self.get_loop().run_until_complete(
                self._call_in_runner_task(asyncgen.asend, None)
            )
        except StopAsyncIteration:
            self._raise_async_exceptions()
        else:
            self.get_loop().run_until_complete(asyncgen.aclose())
            raise RuntimeError("Async generator fixture did not stop")

    def run_fixture(
        self,
        fixture_func: Callable[..., Coroutine[Any, Any, T_Retval]],
        kwargs: dict[str, Any],
    ) -> T_Retval:
        retval = self.get_loop().run_until_complete(
            self._call_in_runner_task(fixture_func, **kwargs)
        )
        self._raise_async_exceptions()
        return retval

    def run_test(
        self, test_func: Callable[..., Coroutine[Any, Any, Any]], kwargs: dict[str, Any]
    ) -> None:
        try:
            self.get_loop().run_until_complete(
                self._call_in_runner_task(test_func, **kwargs)
            )
        except Exception as exc:
            self._exceptions.append(exc)

        self._raise_async_exceptions()


class AsyncIOBackend(AsyncBackend):
    @classmethod
    def run(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        options: dict[str, Any],
    ) -> T_Retval:
        @wraps(func)
        async def wrapper() -> T_Retval:
            task = cast(asyncio.Task, current_task())
            task.set_name(get_callable_name(func))
            _task_states[task] = TaskState(None, None)

            try:
                return await func(*args)
            finally:
                del _task_states[task]

        debug = options.get("debug", None)
        loop_factory = options.get("loop_factory", None)
        if loop_factory is None and options.get("use_uvloop", False):
            import uvloop

            loop_factory = uvloop.new_event_loop

        with Runner(debug=debug, loop_factory=loop_factory) as runner:
            return runner.run(wrapper())

    @classmethod
    def current_token(cls) -> object:
        return get_running_loop()

    @classmethod
    def current_time(cls) -> float:
        return get_running_loop().time()

    @classmethod
    def cancelled_exception_class(cls) -> type[BaseException]:
        return CancelledError

    @classmethod
    async def checkpoint(cls) -> None:
        await sleep(0)

    @classmethod
    async def checkpoint_if_cancelled(cls) -> None:
        task = current_task()
        if task is None:
            return

        try:
            cancel_scope = _task_states[task].cancel_scope
        except KeyError:
            return

        while cancel_scope:
            if cancel_scope.cancel_called:
                await sleep(0)
            elif cancel_scope.shield:
                break
            else:
                cancel_scope = cancel_scope._parent_scope

    @classmethod
    async def cancel_shielded_checkpoint(cls) -> None:
        with CancelScope(shield=True):
            await sleep(0)

    @classmethod
    async def sleep(cls, delay: float) -> None:
        await sleep(delay)

    @classmethod
    def create_cancel_scope(
        cls, *, deadline: float = math.inf, shield: bool = False
    ) -> CancelScope:
        return CancelScope(deadline=deadline, shield=shield)

    @classmethod
    def current_effective_deadline(cls) -> float:
        if (task := current_task()) is None:
            return math.inf

        try:
            cancel_scope = _task_states[task].cancel_scope
        except KeyError:
            return math.inf

        deadline = math.inf
        while cancel_scope:
            deadline = min(deadline, cancel_scope.deadline)
            if cancel_scope._cancel_called:
                deadline = -math.inf
                break
            elif cancel_scope.shield:
                break
            else:
                cancel_scope = cancel_scope._parent_scope

        return deadline

    @classmethod
    def create_task_group(cls) -> abc.TaskGroup:
        return TaskGroup()

    @classmethod
    def create_event(cls) -> abc.Event:
        return Event()

    @classmethod
    def create_lock(cls, *, fast_acquire: bool) -> abc.Lock:
        return Lock(fast_acquire=fast_acquire)

    @classmethod
    def create_semaphore(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> abc.Semaphore:
        return Semaphore(initial_value, max_value=max_value, fast_acquire=fast_acquire)

    @classmethod
    def create_capacity_limiter(cls, total_tokens: float) -> abc.CapacityLimiter:
        return CapacityLimiter(total_tokens)

    @classmethod
    async def run_sync_in_worker_thread(  # type: ignore[return]
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        abandon_on_cancel: bool = False,
        limiter: abc.CapacityLimiter | None = None,
    ) -> T_Retval:
        await cls.checkpoint()

        # If this is the first run in this event loop thread, set up the necessary
        # variables
        try:
            idle_workers = _threadpool_idle_workers.get()
            workers = _threadpool_workers.get()
        except LookupError:
            idle_workers = deque()
            workers = set()
            _threadpool_idle_workers.set(idle_workers)
            _threadpool_workers.set(workers)

        async with limiter or cls.current_default_thread_limiter():
            with CancelScope(shield=not abandon_on_cancel) as scope:
                future = asyncio.Future[T_Retval]()
                root_task = find_root_task()
                if not idle_workers:
                    worker = WorkerThread(root_task, workers, idle_workers)
                    worker.start()
                    workers.add(worker)
                    root_task.add_done_callback(
                        worker.stop, context=contextvars.Context()
                    )
                else:
                    worker = idle_workers.pop()

                    # Prune any other workers that have been idle for MAX_IDLE_TIME
                    # seconds or longer
                    now = cls.current_time()
                    while idle_workers:
                        if (
                            now - idle_workers[0].idle_since
                            < WorkerThread.MAX_IDLE_TIME
                        ):
                            break

                        expired_worker = idle_workers.popleft()
                        expired_worker.root_task.remove_done_callback(
                            expired_worker.stop
                        )
                        expired_worker.stop()

                context = copy_context()
                context.run(sniffio.current_async_library_cvar.set, None)
                if abandon_on_cancel or scope._parent_scope is None:
                    worker_scope = scope
                else:
                    worker_scope = scope._parent_scope

                worker.queue.put_nowait((context, func, args, future, worker_scope))
                return await future

    @classmethod
    def check_cancelled(cls) -> None:
        scope: CancelScope | None = threadlocals.current_cancel_scope
        while scope is not None:
            if scope.cancel_called:
                raise CancelledError(f"Cancelled by cancel scope {id(scope):x}")

            if scope.shield:
                return

            scope = scope._parent_scope

    @classmethod
    def run_async_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        async def task_wrapper(scope: CancelScope) -> T_Retval:
            __tracebackhide__ = True
            task = cast(asyncio.Task, current_task())
            _task_states[task] = TaskState(None, scope)
            scope._tasks.add(task)
            try:
                return await func(*args)
            except CancelledError as exc:
                raise concurrent.futures.CancelledError(str(exc)) from None
            finally:
                scope._tasks.discard(task)

        loop = cast(AbstractEventLoop, token)
        context = copy_context()
        context.run(sniffio.current_async_library_cvar.set, "asyncio")
        wrapper = task_wrapper(threadlocals.current_cancel_scope)
        f: concurrent.futures.Future[T_Retval] = context.run(
            asyncio.run_coroutine_threadsafe, wrapper, loop
        )
        return f.result()

    @classmethod
    def run_sync_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        @wraps(func)
        def wrapper() -> None:
            try:
                sniffio.current_async_library_cvar.set("asyncio")
                f.set_result(func(*args))
            except BaseException as exc:
                f.set_exception(exc)
                if not isinstance(exc, Exception):
                    raise

        f: concurrent.futures.Future[T_Retval] = Future()
        loop = cast(AbstractEventLoop, token)
        loop.call_soon_threadsafe(wrapper)
        return f.result()

    @classmethod
    def create_blocking_portal(cls) -> abc.BlockingPortal:
        return BlockingPortal()

    @classmethod
    async def open_process(
        cls,
        command: StrOrBytesPath | Sequence[StrOrBytesPath],
        *,
        stdin: int | IO[Any] | None,
        stdout: int | IO[Any] | None,
        stderr: int | IO[Any] | None,
        **kwargs: Any,
    ) -> Process:
        await cls.checkpoint()
        if isinstance(command, PathLike):
            command = os.fspath(command)

        if isinstance(command, (str, bytes)):
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                **kwargs,
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                **kwargs,
            )

        stdin_stream = StreamWriterWrapper(process.stdin) if process.stdin else None
        stdout_stream = StreamReaderWrapper(process.stdout) if process.stdout else None
        stderr_stream = StreamReaderWrapper(process.stderr) if process.stderr else None
        return Process(process, stdin_stream, stdout_stream, stderr_stream)

    @classmethod
    def setup_process_pool_exit_at_shutdown(cls, workers: set[abc.Process]) -> None:
        create_task(
            _shutdown_process_pool_on_exit(workers),
            name="AnyIO process pool shutdown task",
        )
        find_root_task().add_done_callback(
            partial(_forcibly_shutdown_process_pool_on_exit, workers)  # type:ignore[arg-type]
        )

    @classmethod
    async def connect_tcp(
        cls, host: str, port: int, local_address: IPSockAddrType | None = None
    ) -> abc.SocketStream:
        transport, protocol = cast(
            tuple[asyncio.Transport, StreamProtocol],
            await get_running_loop().create_connection(
                StreamProtocol, host, port, local_addr=local_address
            ),
        )
        transport.pause_reading()
        return SocketStream(transport, protocol)

    @classmethod
    async def connect_unix(cls, path: str | bytes) -> abc.UNIXSocketStream:
        await cls.checkpoint()
        loop = get_running_loop()
        raw_socket = socket.socket(socket.AF_UNIX)
        raw_socket.setblocking(False)
        while True:
            try:
                raw_socket.connect(path)
            except BlockingIOError:
                f: asyncio.Future = asyncio.Future()
                loop.add_writer(raw_socket, f.set_result, None)
                f.add_done_callback(lambda _: loop.remove_writer(raw_socket))
                await f
            except BaseException:
                raw_socket.close()
                raise
            else:
                return UNIXSocketStream(raw_socket)

    @classmethod
    def create_tcp_listener(cls, sock: socket.socket) -> SocketListener:
        return TCPSocketListener(sock)

    @classmethod
    def create_unix_listener(cls, sock: socket.socket) -> SocketListener:
        return UNIXSocketListener(sock)

    @classmethod
    async def create_udp_socket(
        cls,
        family: AddressFamily,
        local_address: IPSockAddrType | None,
        remote_address: IPSockAddrType | None,
        reuse_port: bool,
    ) -> UDPSocket | ConnectedUDPSocket:
        transport, protocol = await get_running_loop().create_datagram_endpoint(
            DatagramProtocol,
            local_addr=local_address,
            remote_addr=remote_address,
            family=family,
            reuse_port=reuse_port,
        )
        if protocol.exception:
            transport.close()
            raise protocol.exception

        if not remote_address:
            return UDPSocket(transport, protocol)
        else:
            return ConnectedUDPSocket(transport, protocol)

    @classmethod
    async def create_unix_datagram_socket(  # type: ignore[override]
        cls, raw_socket: socket.socket, remote_path: str | bytes | None
    ) -> abc.UNIXDatagramSocket | abc.ConnectedUNIXDatagramSocket:
        await cls.checkpoint()
        loop = get_running_loop()

        if remote_path:
            while True:
                try:
                    raw_socket.connect(remote_path)
                except BlockingIOError:
                    f: asyncio.Future = asyncio.Future()
                    loop.add_writer(raw_socket, f.set_result, None)
                    f.add_done_callback(lambda _: loop.remove_writer(raw_socket))
                    await f
                except BaseException:
                    raw_socket.close()
                    raise
                else:
                    return ConnectedUNIXDatagramSocket(raw_socket)
        else:
            return UNIXDatagramSocket(raw_socket)

    @classmethod
    async def getaddrinfo(
        cls,
        host: bytes | str | None,
        port: str | int | None,
        *,
        family: int | AddressFamily = 0,
        type: int | SocketKind = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> Sequence[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        return await get_running_loop().getaddrinfo(
            host, port, family=family, type=type, proto=proto, flags=flags
        )

    @classmethod
    async def getnameinfo(
        cls, sockaddr: IPSockAddrType, flags: int = 0
    ) -> tuple[str, str]:
        return await get_running_loop().getnameinfo(sockaddr, flags)

    @classmethod
    async def wait_readable(cls, obj: FileDescriptorLike) -> None:
        await cls.checkpoint()
        try:
            read_events = _read_events.get()
        except LookupError:
            read_events = {}
            _read_events.set(read_events)

        if not isinstance(obj, int):
            obj = obj.fileno()

        if read_events.get(obj):
            raise BusyResourceError("reading from")

        loop = get_running_loop()
        event = asyncio.Event()
        try:
            loop.add_reader(obj, event.set)
        except NotImplementedError:
            from anyio._core._asyncio_selector_thread import get_selector

            selector = get_selector()
            selector.add_reader(obj, event.set)
            remove_reader = selector.remove_reader
        else:
            remove_reader = loop.remove_reader

        read_events[obj] = event
        try:
            await event.wait()
        finally:
            remove_reader(obj)
            del read_events[obj]

    @classmethod
    async def wait_writable(cls, obj: FileDescriptorLike) -> None:
        await cls.checkpoint()
        try:
            write_events = _write_events.get()
        except LookupError:
            write_events = {}
            _write_events.set(write_events)

        if not isinstance(obj, int):
            obj = obj.fileno()

        if write_events.get(obj):
            raise BusyResourceError("writing to")

        loop = get_running_loop()
        event = asyncio.Event()
        try:
            loop.add_writer(obj, event.set)
        except NotImplementedError:
            from anyio._core._asyncio_selector_thread import get_selector

            selector = get_selector()
            selector.add_writer(obj, event.set)
            remove_writer = selector.remove_writer
        else:
            remove_writer = loop.remove_writer

        write_events[obj] = event
        try:
            await event.wait()
        finally:
            del write_events[obj]
            remove_writer(obj)

    @classmethod
    def current_default_thread_limiter(cls) -> CapacityLimiter:
        try:
            return _default_thread_limiter.get()
        except LookupError:
            limiter = CapacityLimiter(40)
            _default_thread_limiter.set(limiter)
            return limiter

    @classmethod
    def open_signal_receiver(
        cls, *signals: Signals
    ) -> AbstractContextManager[AsyncIterator[Signals]]:
        return _SignalReceiver(signals)

    @classmethod
    def get_current_task(cls) -> TaskInfo:
        return AsyncIOTaskInfo(current_task())  # type: ignore[arg-type]

    @classmethod
    def get_running_tasks(cls) -> Sequence[TaskInfo]:
        return [AsyncIOTaskInfo(task) for task in all_tasks() if not task.done()]

    @classmethod
    async def wait_all_tasks_blocked(cls) -> None:
        await cls.checkpoint()
        this_task = current_task()
        while True:
            for task in all_tasks():
                if task is this_task:
                    continue

                waiter = task._fut_waiter  # type: ignore[attr-defined]
                if waiter is None or waiter.done():
                    await sleep(0.1)
                    break
            else:
                return

    @classmethod
    def create_test_runner(cls, options: dict[str, Any]) -> TestRunner:
        return TestRunner(**options)


backend_class = AsyncIOBackend

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_pdf.py ===
"""
A PDF Matplotlib backend.

Author: Jouni K Seppänen <jks@iki.fi> and others.
"""

import codecs
from datetime import timezone
from datetime import datetime
from enum import Enum
from functools import total_ordering
from io import BytesIO
import itertools
import logging
import math
import os
import string
import struct
import sys
import time
import types
import warnings
import zlib

import numpy as np
from PIL import Image

import matplotlib as mpl
from matplotlib import _api, _text_helpers, _type1font, cbook, dviread
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, GraphicsContextBase,
    RendererBase)
from matplotlib.backends.backend_mixed import MixedModeRenderer
from matplotlib.figure import Figure
from matplotlib.font_manager import get_font, fontManager as _fontManager
from matplotlib._afm import AFM
from matplotlib.ft2font import FT2Font, FaceFlags, Kerning, LoadFlags, StyleFlags
from matplotlib.transforms import Affine2D, BboxBase
from matplotlib.path import Path
from matplotlib.dates import UTC
from matplotlib import _path
from . import _backend_pdf_ps

_log = logging.getLogger(__name__)

# Overview
#
# The low-level knowledge about pdf syntax lies mainly in the pdfRepr
# function and the classes Reference, Name, Operator, and Stream.  The
# PdfFile class knows about the overall structure of pdf documents.
# It provides a "write" method for writing arbitrary strings in the
# file, and an "output" method that passes objects through the pdfRepr
# function before writing them in the file.  The output method is
# called by the RendererPdf class, which contains the various draw_foo
# methods.  RendererPdf contains a GraphicsContextPdf instance, and
# each draw_foo calls self.check_gc before outputting commands.  This
# method checks whether the pdf graphics state needs to be modified
# and outputs the necessary commands.  GraphicsContextPdf represents
# the graphics state, and its "delta" method returns the commands that
# modify the state.

# Add "pdf.use14corefonts: True" in your configuration file to use only
# the 14 PDF core fonts. These fonts do not need to be embedded; every
# PDF viewing application is required to have them. This results in very
# light PDF files you can use directly in LaTeX or ConTeXt documents
# generated with pdfTeX, without any conversion.

# These fonts are: Helvetica, Helvetica-Bold, Helvetica-Oblique,
# Helvetica-BoldOblique, Courier, Courier-Bold, Courier-Oblique,
# Courier-BoldOblique, Times-Roman, Times-Bold, Times-Italic,
# Times-BoldItalic, Symbol, ZapfDingbats.
#
# Some tricky points:
#
# 1. The clip path can only be widened by popping from the state
# stack.  Thus the state must be pushed onto the stack before narrowing
# the clip path.  This is taken care of by GraphicsContextPdf.
#
# 2. Sometimes it is necessary to refer to something (e.g., font,
# image, or extended graphics state, which contains the alpha value)
# in the page stream by a name that needs to be defined outside the
# stream.  PdfFile provides the methods fontName, imageObject, and
# alphaState for this purpose.  The implementations of these methods
# should perhaps be generalized.

# TODOs:
#
# * encoding of fonts, including mathtext fonts and Unicode support
# * TTF support has lots of small TODOs, e.g., how do you know if a font
#   is serif/sans-serif, or symbolic/non-symbolic?
# * draw_quad_mesh


def _fill(strings, linelen=75):
    """
    Make one string from sequence of strings, with whitespace in between.

    The whitespace is chosen to form lines of at most *linelen* characters,
    if possible.
    """
    currpos = 0
    lasti = 0
    result = []
    for i, s in enumerate(strings):
        length = len(s)
        if currpos + length < linelen:
            currpos += length + 1
        else:
            result.append(b' '.join(strings[lasti:i]))
            lasti = i
            currpos = length
    result.append(b' '.join(strings[lasti:]))
    return b'\n'.join(result)


def _create_pdf_info_dict(backend, metadata):
    """
    Create a PDF infoDict based on user-supplied metadata.

    A default ``Creator``, ``Producer``, and ``CreationDate`` are added, though
    the user metadata may override it. The date may be the current time, or a
    time set by the ``SOURCE_DATE_EPOCH`` environment variable.

    Metadata is verified to have the correct keys and their expected types. Any
    unknown keys/types will raise a warning.

    Parameters
    ----------
    backend : str
        The name of the backend to use in the Producer value.

    metadata : dict[str, Union[str, datetime, Name]]
        A dictionary of metadata supplied by the user with information
        following the PDF specification, also defined in
        `~.backend_pdf.PdfPages` below.

        If any value is *None*, then the key will be removed. This can be used
        to remove any pre-defined values.

    Returns
    -------
    dict[str, Union[str, datetime, Name]]
        A validated dictionary of metadata.
    """

    # get source date from SOURCE_DATE_EPOCH, if set
    # See https://reproducible-builds.org/specs/source-date-epoch/
    source_date_epoch = os.getenv("SOURCE_DATE_EPOCH")
    if source_date_epoch:
        source_date = datetime.fromtimestamp(int(source_date_epoch), timezone.utc)
        source_date = source_date.replace(tzinfo=UTC)
    else:
        source_date = datetime.today()

    info = {
        'Creator': f'Matplotlib v{mpl.__version__}, https://matplotlib.org',
        'Producer': f'Matplotlib {backend} backend v{mpl.__version__}',
        'CreationDate': source_date,
        **metadata
    }
    info = {k: v for (k, v) in info.items() if v is not None}

    def is_string_like(x):
        return isinstance(x, str)
    is_string_like.text_for_warning = "an instance of str"

    def is_date(x):
        return isinstance(x, datetime)
    is_date.text_for_warning = "an instance of datetime.datetime"

    def check_trapped(x):
        if isinstance(x, Name):
            return x.name in (b'True', b'False', b'Unknown')
        else:
            return x in ('True', 'False', 'Unknown')
    check_trapped.text_for_warning = 'one of {"True", "False", "Unknown"}'

    keywords = {
        'Title': is_string_like,
        'Author': is_string_like,
        'Subject': is_string_like,
        'Keywords': is_string_like,
        'Creator': is_string_like,
        'Producer': is_string_like,
        'CreationDate': is_date,
        'ModDate': is_date,
        'Trapped': check_trapped,
    }
    for k in info:
        if k not in keywords:
            _api.warn_external(f'Unknown infodict keyword: {k!r}. '
                               f'Must be one of {set(keywords)!r}.')
        elif not keywords[k](info[k]):
            _api.warn_external(f'Bad value for infodict keyword {k}. '
                               f'Got {info[k]!r} which is not '
                               f'{keywords[k].text_for_warning}.')
    if 'Trapped' in info:
        info['Trapped'] = Name(info['Trapped'])

    return info


def _datetime_to_pdf(d):
    """
    Convert a datetime to a PDF string representing it.

    Used for PDF and PGF.
    """
    r = d.strftime('D:%Y%m%d%H%M%S')
    z = d.utcoffset()
    if z is not None:
        z = z.seconds
    else:
        if time.daylight:
            z = time.altzone
        else:
            z = time.timezone
    if z == 0:
        r += 'Z'
    elif z < 0:
        r += "+%02d'%02d'" % ((-z) // 3600, (-z) % 3600)
    else:
        r += "-%02d'%02d'" % (z // 3600, z % 3600)
    return r


def _calculate_quad_point_coordinates(x, y, width, height, angle=0):
    """
    Calculate the coordinates of rectangle when rotated by angle around x, y
    """

    angle = math.radians(-angle)
    sin_angle = math.sin(angle)
    cos_angle = math.cos(angle)
    a = x + height * sin_angle
    b = y + height * cos_angle
    c = x + width * cos_angle + height * sin_angle
    d = y - width * sin_angle + height * cos_angle
    e = x + width * cos_angle
    f = y - width * sin_angle
    return ((x, y), (e, f), (c, d), (a, b))


def _get_coordinates_of_block(x, y, width, height, angle=0):
    """
    Get the coordinates of rotated rectangle and rectangle that covers the
    rotated rectangle.
    """

    vertices = _calculate_quad_point_coordinates(x, y, width,
                                                 height, angle)

    # Find min and max values for rectangle
    # adjust so that QuadPoints is inside Rect
    # PDF docs says that QuadPoints should be ignored if any point lies
    # outside Rect, but for Acrobat it is enough that QuadPoints is on the
    # border of Rect.

    pad = 0.00001 if angle % 90 else 0
    min_x = min(v[0] for v in vertices) - pad
    min_y = min(v[1] for v in vertices) - pad
    max_x = max(v[0] for v in vertices) + pad
    max_y = max(v[1] for v in vertices) + pad
    return (tuple(itertools.chain.from_iterable(vertices)),
            (min_x, min_y, max_x, max_y))


def _get_link_annotation(gc, x, y, width, height, angle=0):
    """
    Create a link annotation object for embedding URLs.
    """
    quadpoints, rect = _get_coordinates_of_block(x, y, width, height, angle)
    link_annotation = {
        'Type': Name('Annot'),
        'Subtype': Name('Link'),
        'Rect': rect,
        'Border': [0, 0, 0],
        'A': {
            'S': Name('URI'),
            'URI': gc.get_url(),
        },
    }
    if angle % 90:
        # Add QuadPoints
        link_annotation['QuadPoints'] = quadpoints
    return link_annotation


# PDF strings are supposed to be able to include any eight-bit data, except
# that unbalanced parens and backslashes must be escaped by a backslash.
# However, sf bug #2708559 shows that the carriage return character may get
# read as a newline; these characters correspond to \gamma and \Omega in TeX's
# math font encoding. Escaping them fixes the bug.
_str_escapes = str.maketrans({
    '\\': '\\\\', '(': '\\(', ')': '\\)', '\n': '\\n', '\r': '\\r'})


def pdfRepr(obj):
    """Map Python objects to PDF syntax."""

    # Some objects defined later have their own pdfRepr method.
    if hasattr(obj, 'pdfRepr'):
        return obj.pdfRepr()

    # Floats. PDF does not have exponential notation (1.0e-10) so we
    # need to use %f with some precision.  Perhaps the precision
    # should adapt to the magnitude of the number?
    elif isinstance(obj, (float, np.floating)):
        if not np.isfinite(obj):
            raise ValueError("Can only output finite numbers in PDF")
        r = b"%.10f" % obj
        return r.rstrip(b'0').rstrip(b'.')

    # Booleans. Needs to be tested before integers since
    # isinstance(True, int) is true.
    elif isinstance(obj, bool):
        return [b'false', b'true'][obj]

    # Integers are written as such.
    elif isinstance(obj, (int, np.integer)):
        return b"%d" % obj

    # Non-ASCII Unicode strings are encoded in UTF-16BE with byte-order mark.
    elif isinstance(obj, str):
        return pdfRepr(obj.encode('ascii') if obj.isascii()
                       else codecs.BOM_UTF16_BE + obj.encode('UTF-16BE'))

    # Strings are written in parentheses, with backslashes and parens
    # escaped. Actually balanced parens are allowed, but it is
    # simpler to escape them all. TODO: cut long strings into lines;
    # I believe there is some maximum line length in PDF.
    # Despite the extra decode/encode, translate is faster than regex.
    elif isinstance(obj, bytes):
        return (
            b'(' +
            obj.decode('latin-1').translate(_str_escapes).encode('latin-1')
            + b')')

    # Dictionaries. The keys must be PDF names, so if we find strings
    # there, we make Name objects from them. The values may be
    # anything, so the caller must ensure that PDF names are
    # represented as Name objects.
    elif isinstance(obj, dict):
        return _fill([
            b"<<",
            *[Name(k).pdfRepr() + b" " + pdfRepr(v) for k, v in obj.items()],
            b">>",
        ])

    # Lists.
    elif isinstance(obj, (list, tuple)):
        return _fill([b"[", *[pdfRepr(val) for val in obj], b"]"])

    # The null keyword.
    elif obj is None:
        return b'null'

    # A date.
    elif isinstance(obj, datetime):
        return pdfRepr(_datetime_to_pdf(obj))

    # A bounding box
    elif isinstance(obj, BboxBase):
        return _fill([pdfRepr(val) for val in obj.bounds])

    else:
        raise TypeError(f"Don't know a PDF representation for {type(obj)} "
                        "objects")


def _font_supports_glyph(fonttype, glyph):
    """
    Returns True if the font is able to provide codepoint *glyph* in a PDF.

    For a Type 3 font, this method returns True only for single-byte
    characters. For Type 42 fonts this method return True if the character is
    from the Basic Multilingual Plane.
    """
    if fonttype == 3:
        return glyph <= 255
    if fonttype == 42:
        return glyph <= 65535
    raise NotImplementedError()


class Reference:
    """
    PDF reference object.

    Use PdfFile.reserveObject() to create References.
    """

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "<Reference %d>" % self.id

    def pdfRepr(self):
        return b"%d 0 R" % self.id

    def write(self, contents, file):
        write = file.write
        write(b"%d 0 obj\n" % self.id)
        write(pdfRepr(contents))
        write(b"\nendobj\n")


@total_ordering
class Name:
    """PDF name object."""
    __slots__ = ('name',)
    _hexify = {c: '#%02x' % c
               for c in {*range(256)} - {*range(ord('!'), ord('~') + 1)}}

    def __init__(self, name):
        if isinstance(name, Name):
            self.name = name.name
        else:
            if isinstance(name, bytes):
                name = name.decode('ascii')
            self.name = name.translate(self._hexify).encode('ascii')

    def __repr__(self):
        return "<Name %s>" % self.name

    def __str__(self):
        return '/' + self.name.decode('ascii')

    def __eq__(self, other):
        return isinstance(other, Name) and self.name == other.name

    def __lt__(self, other):
        return isinstance(other, Name) and self.name < other.name

    def __hash__(self):
        return hash(self.name)

    def pdfRepr(self):
        return b'/' + self.name


class Verbatim:
    """Store verbatim PDF command content for later inclusion in the stream."""
    def __init__(self, x):
        self._x = x

    def pdfRepr(self):
        return self._x


class Op(Enum):
    """PDF operators (not an exhaustive list)."""

    close_fill_stroke = b'b'
    fill_stroke = b'B'
    fill = b'f'
    closepath = b'h'
    close_stroke = b's'
    stroke = b'S'
    endpath = b'n'
    begin_text = b'BT'
    end_text = b'ET'
    curveto = b'c'
    rectangle = b're'
    lineto = b'l'
    moveto = b'm'
    concat_matrix = b'cm'
    use_xobject = b'Do'
    setgray_stroke = b'G'
    setgray_nonstroke = b'g'
    setrgb_stroke = b'RG'
    setrgb_nonstroke = b'rg'
    setcolorspace_stroke = b'CS'
    setcolorspace_nonstroke = b'cs'
    setcolor_stroke = b'SCN'
    setcolor_nonstroke = b'scn'
    setdash = b'd'
    setlinejoin = b'j'
    setlinecap = b'J'
    setgstate = b'gs'
    gsave = b'q'
    grestore = b'Q'
    textpos = b'Td'
    selectfont = b'Tf'
    textmatrix = b'Tm'
    show = b'Tj'
    showkern = b'TJ'
    setlinewidth = b'w'
    clip = b'W'
    shading = b'sh'

    def pdfRepr(self):
        return self.value

    @classmethod
    def paint_path(cls, fill, stroke):
        """
        Return the PDF operator to paint a path.

        Parameters
        ----------
        fill : bool
            Fill the path with the fill color.
        stroke : bool
            Stroke the outline of the path with the line color.
        """
        if stroke:
            if fill:
                return cls.fill_stroke
            else:
                return cls.stroke
        else:
            if fill:
                return cls.fill
            else:
                return cls.endpath


class Stream:
    """
    PDF stream object.

    This has no pdfRepr method. Instead, call begin(), then output the
    contents of the stream by calling write(), and finally call end().
    """
    __slots__ = ('id', 'len', 'pdfFile', 'file', 'compressobj', 'extra', 'pos')

    def __init__(self, id, len, file, extra=None, png=None):
        """
        Parameters
        ----------
        id : int
            Object id of the stream.
        len : Reference or None
            An unused Reference object for the length of the stream;
            None means to use a memory buffer so the length can be inlined.
        file : PdfFile
            The underlying object to write the stream to.
        extra : dict from Name to anything, or None
            Extra key-value pairs to include in the stream header.
        png : dict or None
            If the data is already png encoded, the decode parameters.
        """
        self.id = id            # object id
        self.len = len          # id of length object
        self.pdfFile = file
        self.file = file.fh      # file to which the stream is written
        self.compressobj = None  # compression object
        if extra is None:
            self.extra = dict()
        else:
            self.extra = extra.copy()
        if png is not None:
            self.extra.update({'Filter':      Name('FlateDecode'),
                               'DecodeParms': png})

        self.pdfFile.recordXref(self.id)
        if mpl.rcParams['pdf.compression'] and not png:
            self.compressobj = zlib.compressobj(
                mpl.rcParams['pdf.compression'])
        if self.len is None:
            self.file = BytesIO()
        else:
            self._writeHeader()
            self.pos = self.file.tell()

    def _writeHeader(self):
        write = self.file.write
        write(b"%d 0 obj\n" % self.id)
        dict = self.extra
        dict['Length'] = self.len
        if mpl.rcParams['pdf.compression']:
            dict['Filter'] = Name('FlateDecode')

        write(pdfRepr(dict))
        write(b"\nstream\n")

    def end(self):
        """Finalize stream."""

        self._flush()
        if self.len is None:
            contents = self.file.getvalue()
            self.len = len(contents)
            self.file = self.pdfFile.fh
            self._writeHeader()
            self.file.write(contents)
            self.file.write(b"\nendstream\nendobj\n")
        else:
            length = self.file.tell() - self.pos
            self.file.write(b"\nendstream\nendobj\n")
            self.pdfFile.writeObject(self.len, length)

    def write(self, data):
        """Write some data on the stream."""

        if self.compressobj is None:
            self.file.write(data)
        else:
            compressed = self.compressobj.compress(data)
            self.file.write(compressed)

    def _flush(self):
        """Flush the compression object."""

        if self.compressobj is not None:
            compressed = self.compressobj.flush()
            self.file.write(compressed)
            self.compressobj = None


def _get_pdf_charprocs(font_path, glyph_ids):
    font = get_font(font_path, hinting_factor=1)
    conv = 1000 / font.units_per_EM  # Conversion to PS units (1/1000's).
    procs = {}
    for glyph_id in glyph_ids:
        g = font.load_glyph(glyph_id, LoadFlags.NO_SCALE)
        # NOTE: We should be using round(), but instead use
        # "(x+.5).astype(int)" to keep backcompat with the old ttconv code
        # (this is different for negative x's).
        d1 = (np.array([g.horiAdvance, 0, *g.bbox]) * conv + .5).astype(int)
        v, c = font.get_path()
        v = (v * 64).astype(int)  # Back to TrueType's internal units (1/64's).
        # Backcompat with old ttconv code: control points between two quads are
        # omitted if they are exactly at the midpoint between the control of
        # the quad before and the quad after, but ttconv used to interpolate
        # *after* conversion to PS units, causing floating point errors.  Here
        # we reproduce ttconv's logic, detecting these "implicit" points and
        # re-interpolating them.  Note that occasionally (e.g. with DejaVu Sans
        # glyph "0") a point detected as "implicit" is actually explicit, and
        # will thus be shifted by 1.
        quads, = np.nonzero(c == 3)
        quads_on = quads[1::2]
        quads_mid_on = np.array(
            sorted({*quads_on} & {*(quads - 1)} & {*(quads + 1)}), int)
        implicit = quads_mid_on[
            (v[quads_mid_on]  # As above, use astype(int), not // division
             == ((v[quads_mid_on - 1] + v[quads_mid_on + 1]) / 2).astype(int))
            .all(axis=1)]
        if (font.postscript_name, glyph_id) in [
                ("DejaVuSerif-Italic", 77),  # j
                ("DejaVuSerif-Italic", 135),  # \AA
        ]:
            v[:, 0] -= 1  # Hard-coded backcompat (FreeType shifts glyph by 1).
        v = (v * conv + .5).astype(int)  # As above re: truncation vs rounding.
        v[implicit] = ((  # Fix implicit points; again, truncate.
            (v[implicit - 1] + v[implicit + 1]) / 2).astype(int))
        procs[font.get_glyph_name(glyph_id)] = (
            " ".join(map(str, d1)).encode("ascii") + b" d1\n"
            + _path.convert_to_string(
                Path(v, c), None, None, False, None, -1,
                # no code for quad Beziers triggers auto-conversion to cubics.
                [b"m", b"l", b"", b"c", b"h"], True)
            + b"f")
    return procs


class PdfFile:
    """PDF file object."""

    def __init__(self, filename, metadata=None):
        """
        Parameters
        ----------
        filename : str or path-like or file-like
            Output target; if a string, a file will be opened for writing.

        metadata : dict from strings to strings and dates
            Information dictionary object (see PDF reference section 10.2.1
            'Document Information Dictionary'), e.g.:
            ``{'Creator': 'My software', 'Author': 'Me', 'Title': 'Awesome'}``.

            The standard keys are 'Title', 'Author', 'Subject', 'Keywords',
            'Creator', 'Producer', 'CreationDate', 'ModDate', and
            'Trapped'. Values have been predefined for 'Creator', 'Producer'
            and 'CreationDate'. They can be removed by setting them to `None`.
        """
        super().__init__()

        self._object_seq = itertools.count(1)  # consumed by reserveObject
        self.xrefTable = [[0, 65535, 'the zero object']]
        self.passed_in_file_object = False
        self.original_file_like = None
        self.tell_base = 0
        fh, opened = cbook.to_filehandle(filename, "wb", return_opened=True)
        if not opened:
            try:
                self.tell_base = filename.tell()
            except OSError:
                fh = BytesIO()
                self.original_file_like = filename
            else:
                fh = filename
                self.passed_in_file_object = True

        self.fh = fh
        self.currentstream = None  # stream object to write to, if any
        fh.write(b"%PDF-1.4\n")    # 1.4 is the first version to have alpha
        # Output some eight-bit chars as a comment so various utilities
        # recognize the file as binary by looking at the first few
        # lines (see note in section 3.4.1 of the PDF reference).
        fh.write(b"%\254\334 \253\272\n")

        self.rootObject = self.reserveObject('root')
        self.pagesObject = self.reserveObject('pages')
        self.pageList = []
        self.fontObject = self.reserveObject('fonts')
        self._extGStateObject = self.reserveObject('extended graphics states')
        self.hatchObject = self.reserveObject('tiling patterns')
        self.gouraudObject = self.reserveObject('Gouraud triangles')
        self.XObjectObject = self.reserveObject('external objects')
        self.resourceObject = self.reserveObject('resources')

        root = {'Type': Name('Catalog'),
                'Pages': self.pagesObject}
        self.writeObject(self.rootObject, root)

        self.infoDict = _create_pdf_info_dict('pdf', metadata or {})

        self.fontNames = {}     # maps filenames to internal font names
        self._internal_font_seq = (Name(f'F{i}') for i in itertools.count(1))
        self.dviFontInfo = {}   # maps dvi font names to embedding information
        # differently encoded Type-1 fonts may share the same descriptor
        self.type1Descriptors = {}
        self._character_tracker = _backend_pdf_ps.CharacterTracker()

        self.alphaStates = {}   # maps alpha values to graphics state objects
        self._alpha_state_seq = (Name(f'A{i}') for i in itertools.count(1))
        self._soft_mask_states = {}
        self._soft_mask_seq = (Name(f'SM{i}') for i in itertools.count(1))
        self._soft_mask_groups = []
        self._hatch_patterns = {}
        self._hatch_pattern_seq = (Name(f'H{i}') for i in itertools.count(1))
        self.gouraudTriangles = []

        self._images = {}
        self._image_seq = (Name(f'I{i}') for i in itertools.count(1))

        self.markers = {}
        self.multi_byte_charprocs = {}

        self.paths = []

        # A list of annotations for each page. Each entry is a tuple of the
        # overall Annots object reference that's inserted into the page object,
        # followed by a list of the actual annotations.
        self._annotations = []
        # For annotations added before a page is created; mostly for the
        # purpose of newTextnote.
        self.pageAnnotations = []

        # The PDF spec recommends to include every procset
        procsets = [Name(x) for x in "PDF Text ImageB ImageC ImageI".split()]

        # Write resource dictionary.
        # Possibly TODO: more general ExtGState (graphics state dictionaries)
        #                ColorSpace Pattern Shading Properties
        resources = {'Font': self.fontObject,
                     'XObject': self.XObjectObject,
                     'ExtGState': self._extGStateObject,
                     'Pattern': self.hatchObject,
                     'Shading': self.gouraudObject,
                     'ProcSet': procsets}
        self.writeObject(self.resourceObject, resources)

    def newPage(self, width, height):
        self.endStream()

        self.width, self.height = width, height
        contentObject = self.reserveObject('page contents')
        annotsObject = self.reserveObject('annotations')
        thePage = {'Type': Name('Page'),
                   'Parent': self.pagesObject,
                   'Resources': self.resourceObject,
                   'MediaBox': [0, 0, 72 * width, 72 * height],
                   'Contents': contentObject,
                   'Annots': annotsObject,
                   }
        pageObject = self.reserveObject('page')
        self.writeObject(pageObject, thePage)
        self.pageList.append(pageObject)
        self._annotations.append((annotsObject, self.pageAnnotations))

        self.beginStream(contentObject.id,
                         self.reserveObject('length of content stream'))
        # Initialize the pdf graphics state to match the default Matplotlib
        # graphics context (colorspace and joinstyle).
        self.output(Name('DeviceRGB'), Op.setcolorspace_stroke)
        self.output(Name('DeviceRGB'), Op.setcolorspace_nonstroke)
        self.output(GraphicsContextPdf.joinstyles['round'], Op.setlinejoin)

        # Clear the list of annotations for the next page
        self.pageAnnotations = []

    def newTextnote(self, text, positionRect=[-100, -100, 0, 0]):
        # Create a new annotation of type text
        theNote = {'Type': Name('Annot'),
                   'Subtype': Name('Text'),
                   'Contents': text,
                   'Rect': positionRect,
                   }
        self.pageAnnotations.append(theNote)

    def _get_subsetted_psname(self, ps_name, charmap):
        def toStr(n, base):
            if n < base:
                return string.ascii_uppercase[n]
            else:
                return (
                    toStr(n // base, base) + string.ascii_uppercase[n % base]
                )

        # encode to string using base 26
        hashed = hash(frozenset(charmap.keys())) % ((sys.maxsize + 1) * 2)
        prefix = toStr(hashed, 26)

        # get first 6 characters from prefix
        return prefix[:6] + "+" + ps_name

    def finalize(self):
        """Write out the various deferred objects and the pdf end matter."""

        self.endStream()
        self._write_annotations()
        self.writeFonts()
        self.writeExtGSTates()
        self._write_soft_mask_groups()
        self.writeHatches()
        self.writeGouraudTriangles()
        xobjects = {
            name: ob for image, name, ob in self._images.values()}
        for tup in self.markers.values():
            xobjects[tup[0]] = tup[1]
        for name, value in self.multi_byte_charprocs.items():
            xobjects[name] = value
        for name, path, trans, ob, join, cap, padding, filled, stroked \
                in self.paths:
            xobjects[name] = ob
        self.writeObject(self.XObjectObject, xobjects)
        self.writeImages()
        self.writeMarkers()
        self.writePathCollectionTemplates()
        self.writeObject(self.pagesObject,
                         {'Type': Name('Pages'),
                          'Kids': self.pageList,
                          'Count': len(self.pageList)})
        self.writeInfoDict()

        # Finalize the file
        self.writeXref()
        self.writeTrailer()

    def close(self):
        """Flush all buffers and free all resources."""

        self.endStream()
        if self.passed_in_file_object:
            self.fh.flush()
        else:
            if self.original_file_like is not None:
                self.original_file_like.write(self.fh.getvalue())
            self.fh.close()

    def write(self, data):
        if self.currentstream is None:
            self.fh.write(data)
        else:
            self.currentstream.write(data)

    def output(self, *data):
        self.write(_fill([pdfRepr(x) for x in data]))
        self.write(b'\n')

    def beginStream(self, id, len, extra=None, png=None):
        assert self.currentstream is None
        self.currentstream = Stream(id, len, self, extra, png)

    def endStream(self):
        if self.currentstream is not None:
            self.currentstream.end()
            self.currentstream = None

    def outputStream(self, ref, data, *, extra=None):
        self.beginStream(ref.id, None, extra)
        self.currentstream.write(data)
        self.endStream()

    def _write_annotations(self):
        for annotsObject, annotations in self._annotations:
            self.writeObject(annotsObject, annotations)

    def fontName(self, fontprop):
        """
        Select a font based on fontprop and return a name suitable for
        Op.selectfont. If fontprop is a string, it will be interpreted
        as the filename of the font.
        """

        if isinstance(fontprop, str):
            filenames = [fontprop]
        elif mpl.rcParams['pdf.use14corefonts']:
            filenames = _fontManager._find_fonts_by_props(
                fontprop, fontext='afm', directory=RendererPdf._afm_font_dir
            )
        else:
            filenames = _fontManager._find_fonts_by_props(fontprop)
        first_Fx = None
        for fname in filenames:
            Fx = self.fontNames.get(fname)
            if not first_Fx:
                first_Fx = Fx
            if Fx is None:
                Fx = next(self._internal_font_seq)
                self.fontNames[fname] = Fx
                _log.debug('Assigning font %s = %r', Fx, fname)
                if not first_Fx:
                    first_Fx = Fx

        # find_fontsprop's first value always adheres to
        # findfont's value, so technically no behaviour change
        return first_Fx

    def dviFontName(self, dvifont):
        """
        Given a dvi font object, return a name suitable for Op.selectfont.
        This registers the font information in ``self.dviFontInfo`` if not yet
        registered.
        """

        dvi_info = self.dviFontInfo.get(dvifont.texname)
        if dvi_info is not None:
            return dvi_info.pdfname

        tex_font_map = dviread.PsfontsMap(dviread.find_tex_file('pdftex.map'))
        psfont = tex_font_map[dvifont.texname]
        if psfont.filename is None:
            raise ValueError(
                "No usable font file found for {} (TeX: {}); "
                "the font may lack a Type-1 version"
                .format(psfont.psname, dvifont.texname))

        pdfname = next(self._internal_font_seq)
        _log.debug('Assigning font %s = %s (dvi)', pdfname, dvifont.texname)
        self.dviFontInfo[dvifont.texname] = types.SimpleNamespace(
            dvifont=dvifont,
            pdfname=pdfname,
            fontfile=psfont.filename,
            basefont=psfont.psname,
            encodingfile=psfont.encoding,
            effects=psfont.effects)
        return pdfname

    def writeFonts(self):
        fonts = {}
        for dviname, info in sorted(self.dviFontInfo.items()):
            Fx = info.pdfname
            _log.debug('Embedding Type-1 font %s from dvi.', dviname)
            fonts[Fx] = self._embedTeXFont(info)
        for filename in sorted(self.fontNames):
            Fx = self.fontNames[filename]
            _log.debug('Embedding font %s.', filename)
            if filename.endswith('.afm'):
                # from pdf.use14corefonts
                _log.debug('Writing AFM font.')
                fonts[Fx] = self._write_afm_font(filename)
            else:
                # a normal TrueType font
                _log.debug('Writing TrueType font.')
                chars = self._character_tracker.used.get(filename)
                if chars:
                    fonts[Fx] = self.embedTTF(filename, chars)
        self.writeObject(self.fontObject, fonts)

    def _write_afm_font(self, filename):
        with open(filename, 'rb') as fh:
            font = AFM(fh)
        fontname = font.get_fontname()
        fontdict = {'Type': Name('Font'),
                    'Subtype': Name('Type1'),
                    'BaseFont': Name(fontname),
                    'Encoding': Name('WinAnsiEncoding')}
        fontdictObject = self.reserveObject('font dictionary')
        self.writeObject(fontdictObject, fontdict)
        return fontdictObject

    def _embedTeXFont(self, fontinfo):
        _log.debug('Embedding TeX font %s - fontinfo=%s',
                   fontinfo.dvifont.texname, fontinfo.__dict__)

        # Widths
        widthsObject = self.reserveObject('font widths')
        self.writeObject(widthsObject, fontinfo.dvifont.widths)

        # Font dictionary
        fontdictObject = self.reserveObject('font dictionary')
        fontdict = {
            'Type':      Name('Font'),
            'Subtype':   Name('Type1'),
            'FirstChar': 0,
            'LastChar':  len(fontinfo.dvifont.widths) - 1,
            'Widths':    widthsObject,
            }

        # Encoding (if needed)
        if fontinfo.encodingfile is not None:
            fontdict['Encoding'] = {
                'Type': Name('Encoding'),
                'Differences': [
                    0, *map(Name, dviread._parse_enc(fontinfo.encodingfile))],
            }

        # If no file is specified, stop short
        if fontinfo.fontfile is None:
            _log.warning(
                "Because of TeX configuration (pdftex.map, see updmap option "
                "pdftexDownloadBase14) the font %s is not embedded. This is "
                "deprecated as of PDF 1.5 and it may cause the consumer "
                "application to show something that was not intended.",
                fontinfo.basefont)
            fontdict['BaseFont'] = Name(fontinfo.basefont)
            self.writeObject(fontdictObject, fontdict)
            return fontdictObject

        # We have a font file to embed - read it in and apply any effects
        t1font = _type1font.Type1Font(fontinfo.fontfile)
        if fontinfo.effects:
            t1font = t1font.transform(fontinfo.effects)
        fontdict['BaseFont'] = Name(t1font.prop['FontName'])

        # Font descriptors may be shared between differently encoded
        # Type-1 fonts, so only create a new descriptor if there is no
        # existing descriptor for this font.
        effects = (fontinfo.effects.get('slant', 0.0),
                   fontinfo.effects.get('extend', 1.0))
        fontdesc = self.type1Descriptors.get((fontinfo.fontfile, effects))
        if fontdesc is None:
            fontdesc = self.createType1Descriptor(t1font, fontinfo.fontfile)
            self.type1Descriptors[(fontinfo.fontfile, effects)] = fontdesc
        fontdict['FontDescriptor'] = fontdesc

        self.writeObject(fontdictObject, fontdict)
        return fontdictObject

    def createType1Descriptor(self, t1font, fontfile):
        # Create and write the font descriptor and the font file
        # of a Type-1 font
        fontdescObject = self.reserveObject('font descriptor')
        fontfileObject = self.reserveObject('font file')

        italic_angle = t1font.prop['ItalicAngle']
        fixed_pitch = t1font.prop['isFixedPitch']

        flags = 0
        # fixed width
        if fixed_pitch:
            flags |= 1 << 0
        # TODO: serif
        if 0:
            flags |= 1 << 1
        # TODO: symbolic (most TeX fonts are)
        if 1:
            flags |= 1 << 2
        # non-symbolic
        else:
            flags |= 1 << 5
        # italic
        if italic_angle:
            flags |= 1 << 6
        # TODO: all caps
        if 0:
            flags |= 1 << 16
        # TODO: small caps
        if 0:
            flags |= 1 << 17
        # TODO: force bold
        if 0:
            flags |= 1 << 18

        ft2font = get_font(fontfile)

        descriptor = {
            'Type':        Name('FontDescriptor'),
            'FontName':    Name(t1font.prop['FontName']),
            'Flags':       flags,
            'FontBBox':    ft2font.bbox,
            'ItalicAngle': italic_angle,
            'Ascent':      ft2font.ascender,
            'Descent':     ft2font.descender,
            'CapHeight':   1000,  # TODO: find this out
            'XHeight':     500,  # TODO: this one too
            'FontFile':    fontfileObject,
            'FontFamily':  t1font.prop['FamilyName'],
            'StemV':       50,  # TODO
            # (see also revision 3874; but not all TeX distros have AFM files!)
            # 'FontWeight': a number where 400 = Regular, 700 = Bold
            }

        self.writeObject(fontdescObject, descriptor)

        self.outputStream(fontfileObject, b"".join(t1font.parts[:2]),
                          extra={'Length1': len(t1font.parts[0]),
                                 'Length2': len(t1font.parts[1]),
                                 'Length3': 0})

        return fontdescObject

    def _get_xobject_glyph_name(self, filename, glyph_name):
        Fx = self.fontName(filename)
        return "-".join([
            Fx.name.decode(),
            os.path.splitext(os.path.basename(filename))[0],
            glyph_name])

    _identityToUnicodeCMap = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo
<< /Registry (Adobe)
   /Ordering (UCS)
   /Supplement 0
>> def
/CMapName /Adobe-Identity-UCS def
/CMapType 2 def
1 begincodespacerange
<0000> <ffff>
endcodespacerange
%d beginbfrange
%s
endbfrange
endcmap
CMapName currentdict /CMap defineresource pop
end
end"""

    def embedTTF(self, filename, characters):
        """Embed the TTF font from the named file into the document."""

        font = get_font(filename)
        fonttype = mpl.rcParams['pdf.fonttype']

        def cvt(length, upe=font.units_per_EM, nearest=True):
            """Convert font coordinates to PDF glyph coordinates."""
            value = length / upe * 1000
            if nearest:
                return round(value)
            # Best(?) to round away from zero for bounding boxes and the like.
            if value < 0:
                return math.floor(value)
            else:
                return math.ceil(value)

        def embedTTFType3(font, characters, descriptor):
            """The Type 3-specific part of embedding a Truetype font"""
            widthsObject = self.reserveObject('font widths')
            fontdescObject = self.reserveObject('font descriptor')
            fontdictObject = self.reserveObject('font dictionary')
            charprocsObject = self.reserveObject('character procs')
            differencesArray = []
            firstchar, lastchar = 0, 255
            bbox = [cvt(x, nearest=False) for x in font.bbox]

            fontdict = {
                'Type': Name('Font'),
                'BaseFont': ps_name,
                'FirstChar': firstchar,
                'LastChar': lastchar,
                'FontDescriptor': fontdescObject,
                'Subtype': Name('Type3'),
                'Name': descriptor['FontName'],
                'FontBBox': bbox,
                'FontMatrix': [.001, 0, 0, .001, 0, 0],
                'CharProcs': charprocsObject,
                'Encoding': {
                    'Type': Name('Encoding'),
                    'Differences': differencesArray},
                'Widths': widthsObject
                }

            from encodings import cp1252

            # Make the "Widths" array
            def get_char_width(charcode):
                s = ord(cp1252.decoding_table[charcode])
                width = font.load_char(
                    s, flags=LoadFlags.NO_SCALE | LoadFlags.NO_HINTING).horiAdvance
                return cvt(width)
            with warnings.catch_warnings():
                # Ignore 'Required glyph missing from current font' warning
                # from ft2font: here we're just building the widths table, but
                # the missing glyphs may not even be used in the actual string.
                warnings.filterwarnings("ignore")
                widths = [get_char_width(charcode)
                          for charcode in range(firstchar, lastchar+1)]
            descriptor['MaxWidth'] = max(widths)

            # Make the "Differences" array, sort the ccodes < 255 from
            # the multi-byte ccodes, and build the whole set of glyph ids
            # that we need from this font.
            glyph_ids = []
            differences = []
            multi_byte_chars = set()
            for c in characters:
                ccode = c
                gind = font.get_char_index(ccode)
                glyph_ids.append(gind)
                glyph_name = font.get_glyph_name(gind)
                if ccode <= 255:
                    differences.append((ccode, glyph_name))
                else:
                    multi_byte_chars.add(glyph_name)
            differences.sort()

            last_c = -2
            for c, name in differences:
                if c != last_c + 1:
                    differencesArray.append(c)
                differencesArray.append(Name(name))
                last_c = c

            # Make the charprocs array.
            rawcharprocs = _get_pdf_charprocs(filename, glyph_ids)
            charprocs = {}
            for charname in sorted(rawcharprocs):
                stream = rawcharprocs[charname]
                charprocDict = {}
                # The 2-byte characters are used as XObjects, so they
                # need extra info in their dictionary
                if charname in multi_byte_chars:
                    charprocDict = {'Type': Name('XObject'),
                                    'Subtype': Name('Form'),
                                    'BBox': bbox}
                    # Each glyph includes bounding box information,
                    # but xpdf and ghostscript can't handle it in a
                    # Form XObject (they segfault!!!), so we remove it
                    # from the stream here.  It's not needed anyway,
                    # since the Form XObject includes it in its BBox
                    # value.
                    stream = stream[stream.find(b"d1") + 2:]
                charprocObject = self.reserveObject('charProc')
                self.outputStream(charprocObject, stream, extra=charprocDict)

                # Send the glyphs with ccode > 255 to the XObject dictionary,
                # and the others to the font itself
                if charname in multi_byte_chars:
                    name = self._get_xobject_glyph_name(filename, charname)
                    self.multi_byte_charprocs[name] = charprocObject
                else:
                    charprocs[charname] = charprocObject

            # Write everything out
            self.writeObject(fontdictObject, fontdict)
            self.writeObject(fontdescObject, descriptor)
            self.writeObject(widthsObject, widths)
            self.writeObject(charprocsObject, charprocs)

            return fontdictObject

        def embedTTFType42(font, characters, descriptor):
            """The Type 42-specific part of embedding a Truetype font"""
            fontdescObject = self.reserveObject('font descriptor')
            cidFontDictObject = self.reserveObject('CID font dictionary')
            type0FontDictObject = self.reserveObject('Type 0 font dictionary')
            cidToGidMapObject = self.reserveObject('CIDToGIDMap stream')
            fontfileObject = self.reserveObject('font file stream')
            wObject = self.reserveObject('Type 0 widths')
            toUnicodeMapObject = self.reserveObject('ToUnicode map')

            subset_str = "".join(chr(c) for c in characters)
            _log.debug("SUBSET %s characters: %s", filename, subset_str)
            with _backend_pdf_ps.get_glyphs_subset(filename, subset_str) as subset:
                fontdata = _backend_pdf_ps.font_as_file(subset)
            _log.debug(
                "SUBSET %s %d -> %d", filename,
                os.stat(filename).st_size, fontdata.getbuffer().nbytes
            )

            # We need this ref for XObjects
            full_font = font

            # reload the font object from the subset
            # (all the necessary data could probably be obtained directly
            # using fontLib.ttLib)
            font = FT2Font(fontdata)

            cidFontDict = {
                'Type': Name('Font'),
                'Subtype': Name('CIDFontType2'),
                'BaseFont': ps_name,
                'CIDSystemInfo': {
                    'Registry': 'Adobe',
                    'Ordering': 'Identity',
                    'Supplement': 0},
                'FontDescriptor': fontdescObject,
                'W': wObject,
                'CIDToGIDMap': cidToGidMapObject
                }

            type0FontDict = {
                'Type': Name('Font'),
                'Subtype': Name('Type0'),
                'BaseFont': ps_name,
                'Encoding': Name('Identity-H'),
                'DescendantFonts': [cidFontDictObject],
                'ToUnicode': toUnicodeMapObject
                }

            # Make fontfile stream
            descriptor['FontFile2'] = fontfileObject
            self.outputStream(
                fontfileObject, fontdata.getvalue(),
                extra={'Length1': fontdata.getbuffer().nbytes})

            # Make the 'W' (Widths) array, CidToGidMap and ToUnicode CMap
            # at the same time
            cid_to_gid_map = ['\0'] * 65536
            widths = []
            max_ccode = 0
            for c in characters:
                ccode = c
                gind = font.get_char_index(ccode)
                glyph = font.load_char(ccode,
                                       flags=LoadFlags.NO_SCALE | LoadFlags.NO_HINTING)
                widths.append((ccode, cvt(glyph.horiAdvance)))
                if ccode < 65536:
                    cid_to_gid_map[ccode] = chr(gind)
                max_ccode = max(ccode, max_ccode)
            widths.sort()
            cid_to_gid_map = cid_to_gid_map[:max_ccode + 1]

            last_ccode = -2
            w = []
            max_width = 0
            unicode_groups = []
            for ccode, width in widths:
                if ccode != last_ccode + 1:
                    w.append(ccode)
                    w.append([width])
                    unicode_groups.append([ccode, ccode])
                else:
                    w[-1].append(width)
                    unicode_groups[-1][1] = ccode
                max_width = max(max_width, width)
                last_ccode = ccode

            unicode_bfrange = []
            for start, end in unicode_groups:
                # Ensure the CID map contains only chars from BMP
                if start > 65535:
                    continue
                end = min(65535, end)

                unicode_bfrange.append(
                    b"<%04x> <%04x> [%s]" %
                    (start, end,
                     b" ".join(b"<%04x>" % x for x in range(start, end+1))))
            unicode_cmap = (self._identityToUnicodeCMap %
                            (len(unicode_groups), b"\n".join(unicode_bfrange)))

            # Add XObjects for unsupported chars
            glyph_ids = []
            for ccode in characters:
                if not _font_supports_glyph(fonttype, ccode):
                    gind = full_font.get_char_index(ccode)
                    glyph_ids.append(gind)

            bbox = [cvt(x, nearest=False) for x in full_font.bbox]
            rawcharprocs = _get_pdf_charprocs(filename, glyph_ids)
            for charname in sorted(rawcharprocs):
                stream = rawcharprocs[charname]
                charprocDict = {'Type': Name('XObject'),
                                'Subtype': Name('Form'),
                                'BBox': bbox}
                # Each glyph includes bounding box information,
                # but xpdf and ghostscript can't handle it in a
                # Form XObject (they segfault!!!), so we remove it
                # from the stream here.  It's not needed anyway,
                # since the Form XObject includes it in its BBox
                # value.
                stream = stream[stream.find(b"d1") + 2:]
                charprocObject = self.reserveObject('charProc')
                self.outputStream(charprocObject, stream, extra=charprocDict)

                name = self._get_xobject_glyph_name(filename, charname)
                self.multi_byte_charprocs[name] = charprocObject

            # CIDToGIDMap stream
            cid_to_gid_map = "".join(cid_to_gid_map).encode("utf-16be")
            self.outputStream(cidToGidMapObject, cid_to_gid_map)

            # ToUnicode CMap
            self.outputStream(toUnicodeMapObject, unicode_cmap)

            descriptor['MaxWidth'] = max_width

            # Write everything out
            self.writeObject(cidFontDictObject, cidFontDict)
            self.writeObject(type0FontDictObject, type0FontDict)
            self.writeObject(fontdescObject, descriptor)
            self.writeObject(wObject, w)

            return type0FontDictObject

        # Beginning of main embedTTF function...

        ps_name = self._get_subsetted_psname(
            font.postscript_name,
            font.get_charmap()
        )
        ps_name = ps_name.encode('ascii', 'replace')
        ps_name = Name(ps_name)
        pclt = font.get_sfnt_table('pclt') or {'capHeight': 0, 'xHeight': 0}
        post = font.get_sfnt_table('post') or {'italicAngle': (0, 0)}
        ff = font.face_flags
        sf = font.style_flags

        flags = 0
        symbolic = False  # ps_name.name in ('Cmsy10', 'Cmmi10', 'Cmex10')
        if FaceFlags.FIXED_WIDTH in ff:
            flags |= 1 << 0
        if 0:  # TODO: serif
            flags |= 1 << 1
        if symbolic:
            flags |= 1 << 2
        else:
            flags |= 1 << 5
        if StyleFlags.ITALIC in sf:
            flags |= 1 << 6
        if 0:  # TODO: all caps
            flags |= 1 << 16
        if 0:  # TODO: small caps
            flags |= 1 << 17
        if 0:  # TODO: force bold
            flags |= 1 << 18

        descriptor = {
            'Type': Name('FontDescriptor'),
            'FontName': ps_name,
            'Flags': flags,
            'FontBBox': [cvt(x, nearest=False) for x in font.bbox],
            'Ascent': cvt(font.ascender, nearest=False),
            'Descent': cvt(font.descender, nearest=False),
            'CapHeight': cvt(pclt['capHeight'], nearest=False),
            'XHeight': cvt(pclt['xHeight']),
            'ItalicAngle': post['italicAngle'][1],  # ???
            'StemV': 0  # ???
            }

        if fonttype == 3:
            return embedTTFType3(font, characters, descriptor)
        elif fonttype == 42:
            return embedTTFType42(font, characters, descriptor)

    def alphaState(self, alpha):
        """Return name of an ExtGState that sets alpha to the given value."""

        state = self.alphaStates.get(alpha, None)
        if state is not None:
            return state[0]

        name = next(self._alpha_state_seq)
        self.alphaStates[alpha] = \
            (name, {'Type': Name('ExtGState'),
                    'CA': alpha[0], 'ca': alpha[1]})
        return name

    def _soft_mask_state(self, smask):
        """
        Return an ExtGState that sets the soft mask to the given shading.

        Parameters
        ----------
        smask : Reference
            Reference to a shading in DeviceGray color space, whose luminosity
            is to be used as the alpha channel.

        Returns
        -------
        Name
        """

        state = self._soft_mask_states.get(smask, None)
        if state is not None:
            return state[0]

        name = next(self._soft_mask_seq)
        groupOb = self.reserveObject('transparency group for soft mask')
        self._soft_mask_states[smask] = (
            name,
            {
                'Type': Name('ExtGState'),
                'AIS': False,
                'SMask': {
                    'Type': Name('Mask'),
                    'S': Name('Luminosity'),
                    'BC': [1],
                    'G': groupOb
                }
            }
        )
        self._soft_mask_groups.append((
            groupOb,
            {
                'Type': Name('XObject'),
                'Subtype': Name('Form'),
                'FormType': 1,
                'Group': {
                    'S': Name('Transparency'),
                    'CS': Name('DeviceGray')
                },
                'Matrix': [1, 0, 0, 1, 0, 0],
                'Resources': {'Shading': {'S': smask}},
                'BBox': [0, 0, 1, 1]
            },
            [Name('S'), Op.shading]
        ))
        return name

    def writeExtGSTates(self):
        self.writeObject(
            self._extGStateObject,
            dict([
                *self.alphaStates.values(),
                *self._soft_mask_states.values()
            ])
        )

    def _write_soft_mask_groups(self):
        for ob, attributes, content in self._soft_mask_groups:
            self.beginStream(ob.id, None, attributes)
            self.output(*content)
            self.endStream()

    def hatchPattern(self, hatch_style):
        # The colors may come in as numpy arrays, which aren't hashable
        edge, face, hatch, lw = hatch_style
        if edge is not None:
            edge = tuple(edge)
        if face is not None:
            face = tuple(face)
        hatch_style = (edge, face, hatch, lw)

        pattern = self._hatch_patterns.get(hatch_style, None)
        if pattern is not None:
            return pattern

        name = next(self._hatch_pattern_seq)
        self._hatch_patterns[hatch_style] = name
        return name

    hatchPatterns = _api.deprecated("3.10")(property(lambda self: {
        k: (e, f, h) for k, (e, f, h, l) in self._hatch_patterns.items()
    }))

    def writeHatches(self):
        hatchDict = dict()
        sidelen = 72.0
        for hatch_style, name in self._hatch_patterns.items():
            ob = self.reserveObject('hatch pattern')
            hatchDict[name] = ob
            res = {'Procsets':
                   [Name(x) for x in "PDF Text ImageB ImageC ImageI".split()]}
            self.beginStream(
                ob.id, None,
                {'Type': Name('Pattern'),
                 'PatternType': 1, 'PaintType': 1, 'TilingType': 1,
                 'BBox': [0, 0, sidelen, sidelen],
                 'XStep': sidelen, 'YStep': sidelen,
                 'Resources': res,
                 # Change origin to match Agg at top-left.
                 'Matrix': [1, 0, 0, 1, 0, self.height * 72]})

            stroke_rgb, fill_rgb, hatch, lw = hatch_style
            self.output(stroke_rgb[0], stroke_rgb[1], stroke_rgb[2],
                        Op.setrgb_stroke)
            if fill_rgb is not None:
                self.output(fill_rgb[0], fill_rgb[1], fill_rgb[2],
                            Op.setrgb_nonstroke,
                            0, 0, sidelen, sidelen, Op.rectangle,
                            Op.fill)

            self.output(lw, Op.setlinewidth)

            self.output(*self.pathOperations(
                Path.hatch(hatch),
                Affine2D().scale(sidelen),
                simplify=False))
            self.output(Op.fill_stroke)

            self.endStream()
        self.writeObject(self.hatchObject, hatchDict)

    def addGouraudTriangles(self, points, colors):
        """
        Add a Gouraud triangle shading.

        Parameters
        ----------
        points : np.ndarray
            Triangle vertices, shape (n, 3, 2)
            where n = number of triangles, 3 = vertices, 2 = x, y.
        colors : np.ndarray
            Vertex colors, shape (n, 3, 1) or (n, 3, 4)
            as with points, but last dimension is either (gray,)
            or (r, g, b, alpha).

        Returns
        -------
        Name, Reference
        """
        name = Name('GT%d' % len(self.gouraudTriangles))
        ob = self.reserveObject(f'Gouraud triangle {name}')
        self.gouraudTriangles.append((name, ob, points, colors))
        return name, ob

    def writeGouraudTriangles(self):
        gouraudDict = dict()
        for name, ob, points, colors in self.gouraudTriangles:
            gouraudDict[name] = ob
            shape = points.shape
            flat_points = points.reshape((shape[0] * shape[1], 2))
            colordim = colors.shape[2]
            assert colordim in (1, 4)
            flat_colors = colors.reshape((shape[0] * shape[1], colordim))
            if colordim == 4:
                # strip the alpha channel
                colordim = 3
            points_min = np.min(flat_points, axis=0) - (1 << 8)
            points_max = np.max(flat_points, axis=0) + (1 << 8)
            factor = 0xffffffff / (points_max - points_min)

            self.beginStream(
                ob.id, None,
                {'ShadingType': 4,
                 'BitsPerCoordinate': 32,
                 'BitsPerComponent': 8,
                 'BitsPerFlag': 8,
                 'ColorSpace': Name(
                     'DeviceRGB' if colordim == 3 else 'DeviceGray'
                 ),
                 'AntiAlias': False,
                 'Decode': ([points_min[0], points_max[0],
                             points_min[1], points_max[1]]
                            + [0, 1] * colordim),
                 })

            streamarr = np.empty(
                (shape[0] * shape[1],),
                dtype=[('flags', 'u1'),
                       ('points', '>u4', (2,)),
                       ('colors', 'u1', (colordim,))])
            streamarr['flags'] = 0
            streamarr['points'] = (flat_points - points_min) * factor
            streamarr['colors'] = flat_colors[:, :colordim] * 255.0

            self.write(streamarr.tobytes())
            self.endStream()
        self.writeObject(self.gouraudObject, gouraudDict)

    def imageObject(self, image):
        """Return name of an image XObject representing the given image."""

        entry = self._images.get(id(image), None)
        if entry is not None:
            return entry[1]

        name = next(self._image_seq)
        ob = self.reserveObject(f'image {name}')
        self._images[id(image)] = (image, name, ob)
        return name

    def _unpack(self, im):
        """
        Unpack image array *im* into ``(data, alpha)``, which have shape
        ``(height, width, 3)`` (RGB) or ``(height, width, 1)`` (grayscale or
        alpha), except that alpha is None if the image is fully opaque.
        """
        im = im[::-1]
        if im.ndim == 2:
            return im, None
        else:
            rgb = im[:, :, :3]
            rgb = np.array(rgb, order='C')
            # PDF needs a separate alpha image
            if im.shape[2] == 4:
                alpha = im[:, :, 3][..., None]
                if np.all(alpha == 255):
                    alpha = None
                else:
                    alpha = np.array(alpha, order='C')
            else:
                alpha = None
            return rgb, alpha

    def _writePng(self, img):
        """
        Write the image *img* into the pdf file using png
        predictors with Flate compression.
        """
        buffer = BytesIO()
        img.save(buffer, format="png")
        buffer.seek(8)
        png_data = b''
        bit_depth = palette = None
        while True:
            length, type = struct.unpack(b'!L4s', buffer.read(8))
            if type in [b'IHDR', b'PLTE', b'IDAT']:
                data = buffer.read(length)
                if len(data) != length:
                    raise RuntimeError("truncated data")
                if type == b'IHDR':
                    bit_depth = int(data[8])
                elif type == b'PLTE':
                    palette = data
                elif type == b'IDAT':
                    png_data += data
            elif type == b'IEND':
                break
            else:
                buffer.seek(length, 1)
            buffer.seek(4, 1)   # skip CRC
        return png_data, bit_depth, palette

    def _writeImg(self, data, id, smask=None):
        """
        Write the image *data*, of shape ``(height, width, 1)`` (grayscale) or
        ``(height, width, 3)`` (RGB), as pdf object *id* and with the soft mask
        (alpha channel) *smask*, which should be either None or a ``(height,
        width, 1)`` array.
        """
        height, width, color_channels = data.shape
        obj = {'Type': Name('XObject'),
               'Subtype': Name('Image'),
               'Width': width,
               'Height': height,
               'ColorSpace': Name({1: 'DeviceGray', 3: 'DeviceRGB'}[color_channels]),
               'BitsPerComponent': 8}
        if smask:
            obj['SMask'] = smask
        if mpl.rcParams['pdf.compression']:
            if data.shape[-1] == 1:
                data = data.squeeze(axis=-1)
            png = {'Predictor': 10, 'Colors': color_channels, 'Columns': width}
            img = Image.fromarray(data)
            img_colors = img.getcolors(maxcolors=256)
            if color_channels == 3 and img_colors is not None:
                # Convert to indexed color if there are 256 colors or fewer. This can
                # significantly reduce the file size.
                num_colors = len(img_colors)
                palette = np.array([comp for _, color in img_colors for comp in color],
                                   dtype=np.uint8)
                palette24 = ((palette[0::3].astype(np.uint32) << 16) |
                             (palette[1::3].astype(np.uint32) << 8) |
                             palette[2::3])
                rgb24 = ((data[:, :, 0].astype(np.uint32) << 16) |
                         (data[:, :, 1].astype(np.uint32) << 8) |
                         data[:, :, 2])
                indices = np.argsort(palette24).astype(np.uint8)
                rgb8 = indices[np.searchsorted(palette24, rgb24, sorter=indices)]
                img = Image.fromarray(rgb8, mode='P')
                img.putpalette(palette)
                png_data, bit_depth, palette = self._writePng(img)
                if bit_depth is None or palette is None:
                    raise RuntimeError("invalid PNG header")
                palette = palette[:num_colors * 3]  # Trim padding; remove for Pillow>=9
                obj['ColorSpace'] = [Name('Indexed'), Name('DeviceRGB'),
                                     num_colors - 1, palette]
                obj['BitsPerComponent'] = bit_depth
                png['Colors'] = 1
                png['BitsPerComponent'] = bit_depth
            else:
                png_data, _, _ = self._writePng(img)
        else:
            png = None
        self.beginStream(
            id,
            self.reserveObject('length of image stream'),
            obj,
            png=png
            )
        if png:
            self.currentstream.write(png_data)
        else:
            self.currentstream.write(data.tobytes())
        self.endStream()

    def writeImages(self):
        for img, name, ob in self._images.values():
            data, adata = self._unpack(img)
            if adata is not None:
                smaskObject = self.reserveObject("smask")
                self._writeImg(adata, smaskObject.id)
            else:
                smaskObject = None
            self._writeImg(data, ob.id, smaskObject)

    def markerObject(self, path, trans, fill, stroke, lw, joinstyle,
                     capstyle):
        """Return name of a marker XObject representing the given path."""
        # self.markers used by markerObject, writeMarkers, close:
        # mapping from (path operations, fill?, stroke?) to
        #   [name, object reference, bounding box, linewidth]
        # This enables different draw_markers calls to share the XObject
        # if the gc is sufficiently similar: colors etc can vary, but
        # the choices of whether to fill and whether to stroke cannot.
        # We need a bounding box enclosing all of the XObject path,
        # but since line width may vary, we store the maximum of all
        # occurring line widths in self.markers.
        # close() is somewhat tightly coupled in that it expects the
        # first two components of each value in self.markers to be the
        # name and object reference.
        pathops = self.pathOperations(path, trans, simplify=False)
        key = (tuple(pathops), bool(fill), bool(stroke), joinstyle, capstyle)
        result = self.markers.get(key)
        if result is None:
            name = Name('M%d' % len(self.markers))
            ob = self.reserveObject('marker %d' % len(self.markers))
            bbox = path.get_extents(trans)
            self.markers[key] = [name, ob, bbox, lw]
        else:
            if result[-1] < lw:
                result[-1] = lw
            name = result[0]
        return name

    def writeMarkers(self):
        for ((pathops, fill, stroke, joinstyle, capstyle),
             (name, ob, bbox, lw)) in self.markers.items():
            # bbox wraps the exact limits of the control points, so half a line
            # will appear outside it. If the join style is miter and the line
            # is not parallel to the edge, then the line will extend even
            # further. From the PDF specification, Section 8.4.3.5, the miter
            # limit is miterLength / lineWidth and from Table 52, the default
            # is 10. With half the miter length outside, that works out to the
            # following padding:
            bbox = bbox.padded(lw * 5)
            self.beginStream(
                ob.id, None,
                {'Type': Name('XObject'), 'Subtype': Name('Form'),
                 'BBox': list(bbox.extents)})
            self.output(GraphicsContextPdf.joinstyles[joinstyle],
                        Op.setlinejoin)
            self.output(GraphicsContextPdf.capstyles[capstyle], Op.setlinecap)
            self.output(*pathops)
            self.output(Op.paint_path(fill, stroke))
            self.endStream()

    def pathCollectionObject(self, gc, path, trans, padding, filled, stroked):
        name = Name('P%d' % len(self.paths))
        ob = self.reserveObject('path %d' % len(self.paths))
        self.paths.append(
            (name, path, trans, ob, gc.get_joinstyle(), gc.get_capstyle(),
             padding, filled, stroked))
        return name

    def writePathCollectionTemplates(self):
        for (name, path, trans, ob, joinstyle, capstyle, padding, filled,
             stroked) in self.paths:
            pathops = self.pathOperations(path, trans, simplify=False)
            bbox = path.get_extents(trans)
            if not np.all(np.isfinite(bbox.extents)):
                extents = [0, 0, 0, 0]
            else:
                bbox = bbox.padded(padding)
                extents = list(bbox.extents)
            self.beginStream(
                ob.id, None,
                {'Type': Name('XObject'), 'Subtype': Name('Form'),
                 'BBox': extents})
            self.output(GraphicsContextPdf.joinstyles[joinstyle],
                        Op.setlinejoin)
            self.output(GraphicsContextPdf.capstyles[capstyle], Op.setlinecap)
            self.output(*pathops)
            self.output(Op.paint_path(filled, stroked))
            self.endStream()

    @staticmethod
    def pathOperations(path, transform, clip=None, simplify=None, sketch=None):
        return [Verbatim(_path.convert_to_string(
            path, transform, clip, simplify, sketch,
            6,
            [Op.moveto.value, Op.lineto.value, b'', Op.curveto.value,
             Op.closepath.value],
            True))]

    def writePath(self, path, transform, clip=False, sketch=None):
        if clip:
            clip = (0.0, 0.0, self.width * 72, self.height * 72)
            simplify = path.should_simplify
        else:
            clip = None
            simplify = False
        cmds = self.pathOperations(path, transform, clip, simplify=simplify,
                                   sketch=sketch)
        self.output(*cmds)

    def reserveObject(self, name=''):
        """
        Reserve an ID for an indirect object.

        The name is used for debugging in case we forget to print out
        the object with writeObject.
        """
        id = next(self._object_seq)
        self.xrefTable.append([None, 0, name])
        return Reference(id)

    def recordXref(self, id):
        self.xrefTable[id][0] = self.fh.tell() - self.tell_base

    def writeObject(self, object, contents):
        self.recordXref(object.id)
        object.write(contents, self)

    def writeXref(self):
        """Write out the xref table."""
        self.startxref = self.fh.tell() - self.tell_base
        self.write(b"xref\n0 %d\n" % len(self.xrefTable))
        for i, (offset, generation, name) in enumerate(self.xrefTable):
            if offset is None:
                raise AssertionError(
                    'No offset for object %d (%s)' % (i, name))
            else:
                key = b"f" if name == 'the zero object' else b"n"
                text = b"%010d %05d %b \n" % (offset, generation, key)
                self.write(text)

    def writeInfoDict(self):
        """Write out the info dictionary, checking it for good form"""

        self.infoObject = self.reserveObject('info')
        self.writeObject(self.infoObject, self.infoDict)

    def writeTrailer(self):
        """Write out the PDF trailer."""

        self.write(b"trailer\n")
        self.write(pdfRepr(
            {'Size': len(self.xrefTable),
             'Root': self.rootObject,
             'Info': self.infoObject}))
        # Could add 'ID'
        self.write(b"\nstartxref\n%d\n%%%%EOF\n" % self.startxref)


class RendererPdf(_backend_pdf_ps.RendererPDFPSBase):

    _afm_font_dir = cbook._get_data_path("fonts/pdfcorefonts")
    _use_afm_rc_name = "pdf.use14corefonts"

    def __init__(self, file, image_dpi, height, width):
        super().__init__(width, height)
        self.file = file
        self.gc = self.new_gc()
        self.image_dpi = image_dpi

    def finalize(self):
        self.file.output(*self.gc.finalize())

    def check_gc(self, gc, fillcolor=None):
        orig_fill = getattr(gc, '_fillcolor', (0., 0., 0.))
        gc._fillcolor = fillcolor

        orig_alphas = getattr(gc, '_effective_alphas', (1.0, 1.0))

        if gc.get_rgb() is None:
            # It should not matter what color here since linewidth should be
            # 0 unless affected by global settings in rcParams, hence setting
            # zero alpha just in case.
            gc.set_foreground((0, 0, 0, 0), isRGBA=True)

        if gc._forced_alpha:
            gc._effective_alphas = (gc._alpha, gc._alpha)
        elif fillcolor is None or len(fillcolor) < 4:
            gc._effective_alphas = (gc._rgb[3], 1.0)
        else:
            gc._effective_alphas = (gc._rgb[3], fillcolor[3])

        delta = self.gc.delta(gc)
        if delta:
            self.file.output(*delta)

        # Restore gc to avoid unwanted side effects
        gc._fillcolor = orig_fill
        gc._effective_alphas = orig_alphas

    def get_image_magnification(self):
        return self.image_dpi/72.0

    def draw_image(self, gc, x, y, im, transform=None):
        # docstring inherited

        h, w = im.shape[:2]
        if w == 0 or h == 0:
            return

        if transform is None:
            # If there's no transform, alpha has already been applied
            gc.set_alpha(1.0)

        self.check_gc(gc)

        w = 72.0 * w / self.image_dpi
        h = 72.0 * h / self.image_dpi

        imob = self.file.imageObject(im)

        if transform is None:
            self.file.output(Op.gsave,
                             w, 0, 0, h, x, y, Op.concat_matrix,
                             imob, Op.use_xobject, Op.grestore)
        else:
            tr1, tr2, tr3, tr4, tr5, tr6 = transform.frozen().to_values()

            self.file.output(Op.gsave,
                             1, 0, 0, 1, x, y, Op.concat_matrix,
                             tr1, tr2, tr3, tr4, tr5, tr6, Op.concat_matrix,
                             imob, Op.use_xobject, Op.grestore)

    def draw_path(self, gc, path, transform, rgbFace=None):
        # docstring inherited
        self.check_gc(gc, rgbFace)
        self.file.writePath(
            path, transform,
            rgbFace is None and gc.get_hatch_path() is None,
            gc.get_sketch_params())
        self.file.output(self.gc.paint())

    def draw_path_collection(self, gc, master_transform, paths, all_transforms,
                             offsets, offset_trans, facecolors, edgecolors,
                             linewidths, linestyles, antialiaseds, urls,
                             offset_position):
        # We can only reuse the objects if the presence of fill and
        # stroke (and the amount of alpha for each) is the same for
        # all of them
        can_do_optimization = True
        facecolors = np.asarray(facecolors)
        edgecolors = np.asarray(edgecolors)

        if not len(facecolors):
            filled = False
            can_do_optimization = not gc.get_hatch()
        else:
            if np.all(facecolors[:, 3] == facecolors[0, 3]):
                filled = facecolors[0, 3] != 0.0
            else:
                can_do_optimization = False

        if not len(edgecolors):
            stroked = False
        else:
            if np.all(np.asarray(linewidths) == 0.0):
                stroked = False
            elif np.all(edgecolors[:, 3] == edgecolors[0, 3]):
                stroked = edgecolors[0, 3] != 0.0
            else:
                can_do_optimization = False

        # Is the optimization worth it? Rough calculation:
        # cost of emitting a path in-line is len_path * uses_per_path
        # cost of XObject is len_path + 5 for the definition,
        #    uses_per_path for the uses
        len_path = len(paths[0].vertices) if len(paths) > 0 else 0
        uses_per_path = self._iter_collection_uses_per_path(
            paths, all_transforms, offsets, facecolors, edgecolors)
        should_do_optimization = \
            len_path + uses_per_path + 5 < len_path * uses_per_path

        if (not can_do_optimization) or (not should_do_optimization):
            return RendererBase.draw_path_collection(
                self, gc, master_transform, paths, all_transforms,
                offsets, offset_trans, facecolors, edgecolors,
                linewidths, linestyles, antialiaseds, urls,
                offset_position)

        padding = np.max(linewidths)
        path_codes = []
        for i, (path, transform) in enumerate(self._iter_collection_raw_paths(
                master_transform, paths, all_transforms)):
            name = self.file.pathCollectionObject(
                gc, path, transform, padding, filled, stroked)
            path_codes.append(name)

        output = self.file.output
        output(*self.gc.push())
        lastx, lasty = 0, 0
        for xo, yo, path_id, gc0, rgbFace in self._iter_collection(
                gc, path_codes, offsets, offset_trans,
                facecolors, edgecolors, linewidths, linestyles,
                antialiaseds, urls, offset_position):

            self.check_gc(gc0, rgbFace)
            dx, dy = xo - lastx, yo - lasty
            output(1, 0, 0, 1, dx, dy, Op.concat_matrix, path_id,
                   Op.use_xobject)
            lastx, lasty = xo, yo
        output(*self.gc.pop())

    def draw_markers(self, gc, marker_path, marker_trans, path, trans,
                     rgbFace=None):
        # docstring inherited

        # Same logic as in draw_path_collection
        len_marker_path = len(marker_path)
        uses = len(path)
        if len_marker_path * uses < len_marker_path + uses + 5:
            RendererBase.draw_markers(self, gc, marker_path, marker_trans,
                                      path, trans, rgbFace)
            return

        self.check_gc(gc, rgbFace)
        fill = gc.fill(rgbFace)
        stroke = gc.stroke()

        output = self.file.output
        marker = self.file.markerObject(
            marker_path, marker_trans, fill, stroke, self.gc._linewidth,
            gc.get_joinstyle(), gc.get_capstyle())

        output(Op.gsave)
        lastx, lasty = 0, 0
        for vertices, code in path.iter_segments(
                trans,
                clip=(0, 0, self.file.width*72, self.file.height*72),
                simplify=False):
            if len(vertices):
                x, y = vertices[-2:]
                if not (0 <= x <= self.file.width * 72
                        and 0 <= y <= self.file.height * 72):
                    continue
                dx, dy = x - lastx, y - lasty
                output(1, 0, 0, 1, dx, dy, Op.concat_matrix,
                       marker, Op.use_xobject)
                lastx, lasty = x, y
        output(Op.grestore)

    def draw_gouraud_triangles(self, gc, points, colors, trans):
        assert len(points) == len(colors)
        if len(points) == 0:
            return
        assert points.ndim == 3
        assert points.shape[1] == 3
        assert points.shape[2] == 2
        assert colors.ndim == 3
        assert colors.shape[1] == 3
        assert colors.shape[2] in (1, 4)

        shape = points.shape
        points = points.reshape((shape[0] * shape[1], 2))
        tpoints = trans.transform(points)
        tpoints = tpoints.reshape(shape)
        name, _ = self.file.addGouraudTriangles(tpoints, colors)
        output = self.file.output

        if colors.shape[2] == 1:
            # grayscale
            gc.set_alpha(1.0)
            self.check_gc(gc)
            output(name, Op.shading)
            return

        alpha = colors[0, 0, 3]
        if np.allclose(alpha, colors[:, :, 3]):
            # single alpha value
            gc.set_alpha(alpha)
            self.check_gc(gc)
            output(name, Op.shading)
        else:
            # varying alpha: use a soft mask
            alpha = colors[:, :, 3][:, :, None]
            _, smask_ob = self.file.addGouraudTriangles(tpoints, alpha)
            gstate = self.file._soft_mask_state(smask_ob)
            output(Op.gsave, gstate, Op.setgstate,
                   name, Op.shading,
                   Op.grestore)

    def _setup_textpos(self, x, y, angle, oldx=0, oldy=0, oldangle=0):
        if angle == oldangle == 0:
            self.file.output(x - oldx, y - oldy, Op.textpos)
        else:
            angle = math.radians(angle)
            self.file.output(math.cos(angle), math.sin(angle),
                             -math.sin(angle), math.cos(angle),
                             x, y, Op.textmatrix)
            self.file.output(0, 0, Op.textpos)

    def draw_mathtext(self, gc, x, y, s, prop, angle):
        # TODO: fix positioning and encoding
        width, height, descent, glyphs, rects = \
            self._text2path.mathtext_parser.parse(s, 72, prop)

        if gc.get_url() is not None:
            self.file._annotations[-1][1].append(_get_link_annotation(
                gc, x, y, width, height, angle))

        fonttype = mpl.rcParams['pdf.fonttype']

        # Set up a global transformation matrix for the whole math expression
        a = math.radians(angle)
        self.file.output(Op.gsave)
        self.file.output(math.cos(a), math.sin(a),
                         -math.sin(a), math.cos(a),
                         x, y, Op.concat_matrix)

        self.check_gc(gc, gc._rgb)
        prev_font = None, None
        oldx, oldy = 0, 0
        unsupported_chars = []

        self.file.output(Op.begin_text)
        for font, fontsize, num, ox, oy in glyphs:
            self.file._character_tracker.track_glyph(font, num)
            fontname = font.fname
            if not _font_supports_glyph(fonttype, num):
                # Unsupported chars (i.e. multibyte in Type 3 or beyond BMP in
                # Type 42) must be emitted separately (below).
                unsupported_chars.append((font, fontsize, ox, oy, num))
            else:
                self._setup_textpos(ox, oy, 0, oldx, oldy)
                oldx, oldy = ox, oy
                if (fontname, fontsize) != prev_font:
                    self.file.output(self.file.fontName(fontname), fontsize,
                                     Op.selectfont)
                    prev_font = fontname, fontsize
                self.file.output(self.encode_string(chr(num), fonttype),
                                 Op.show)
        self.file.output(Op.end_text)

        for font, fontsize, ox, oy, num in unsupported_chars:
            self._draw_xobject_glyph(
                font, fontsize, font.get_char_index(num), ox, oy)

        # Draw any horizontal lines in the math layout
        for ox, oy, width, height in rects:
            self.file.output(Op.gsave, ox, oy, width, height,
                             Op.rectangle, Op.fill, Op.grestore)

        # Pop off the global transformation
        self.file.output(Op.grestore)

    def draw_tex(self, gc, x, y, s, prop, angle, *, mtext=None):
        # docstring inherited
        texmanager = self.get_texmanager()
        fontsize = prop.get_size_in_points()
        dvifile = texmanager.make_dvi(s, fontsize)
        with dviread.Dvi(dvifile, 72) as dvi:
            page, = dvi

        if gc.get_url() is not None:
            self.file._annotations[-1][1].append(_get_link_annotation(
                gc, x, y, page.width, page.height, angle))

        # Gather font information and do some setup for combining
        # characters into strings. The variable seq will contain a
        # sequence of font and text entries. A font entry is a list
        # ['font', name, size] where name is a Name object for the
        # font. A text entry is ['text', x, y, glyphs, x+w] where x
        # and y are the starting coordinates, w is the width, and
        # glyphs is a list; in this phase it will always contain just
        # one single-character string, but later it may have longer
        # strings interspersed with kern amounts.
        oldfont, seq = None, []
        for x1, y1, dvifont, glyph, width in page.text:
            if dvifont != oldfont:
                pdfname = self.file.dviFontName(dvifont)
                seq += [['font', pdfname, dvifont.size]]
                oldfont = dvifont
            seq += [['text', x1, y1, [bytes([glyph])], x1+width]]

        # Find consecutive text strings with constant y coordinate and
        # combine into a sequence of strings and kerns, or just one
        # string (if any kerns would be less than 0.1 points).
        i, curx, fontsize = 0, 0, None
        while i < len(seq)-1:
            elt, nxt = seq[i:i+2]
            if elt[0] == 'font':
                fontsize = elt[2]
            elif elt[0] == nxt[0] == 'text' and elt[2] == nxt[2]:
                offset = elt[4] - nxt[1]
                if abs(offset) < 0.1:
                    elt[3][-1] += nxt[3][0]
                    elt[4] += nxt[4]-nxt[1]
                else:
                    elt[3] += [offset*1000.0/fontsize, nxt[3][0]]
                    elt[4] = nxt[4]
                del seq[i+1]
                continue
            i += 1

        # Create a transform to map the dvi contents to the canvas.
        mytrans = Affine2D().rotate_deg(angle).translate(x, y)

        # Output the text.
        self.check_gc(gc, gc._rgb)
        self.file.output(Op.begin_text)
        curx, cury, oldx, oldy = 0, 0, 0, 0
        for elt in seq:
            if elt[0] == 'font':
                self.file.output(elt[1], elt[2], Op.selectfont)
            elif elt[0] == 'text':
                curx, cury = mytrans.transform((elt[1], elt[2]))
                self._setup_textpos(curx, cury, angle, oldx, oldy)
                oldx, oldy = curx, cury
                if len(elt[3]) == 1:
                    self.file.output(elt[3][0], Op.show)
                else:
                    self.file.output(elt[3], Op.showkern)
            else:
                assert False
        self.file.output(Op.end_text)

        # Then output the boxes (e.g., variable-length lines of square
        # roots).
        boxgc = self.new_gc()
        boxgc.copy_properties(gc)
        boxgc.set_linewidth(0)
        pathops = [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO,
                   Path.CLOSEPOLY]
        for x1, y1, h, w in page.boxes:
            path = Path([[x1, y1], [x1+w, y1], [x1+w, y1+h], [x1, y1+h],
                         [0, 0]], pathops)
            self.draw_path(boxgc, path, mytrans, gc._rgb)

    def encode_string(self, s, fonttype):
        if fonttype in (1, 3):
            return s.encode('cp1252', 'replace')
        return s.encode('utf-16be', 'replace')

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        # docstring inherited

        # TODO: combine consecutive texts into one BT/ET delimited section

        self.check_gc(gc, gc._rgb)
        if ismath:
            return self.draw_mathtext(gc, x, y, s, prop, angle)

        fontsize = prop.get_size_in_points()

        if mpl.rcParams['pdf.use14corefonts']:
            font = self._get_font_afm(prop)
            fonttype = 1
        else:
            font = self._get_font_ttf(prop)
            self.file._character_tracker.track(font, s)
            fonttype = mpl.rcParams['pdf.fonttype']

        if gc.get_url() is not None:
            font.set_text(s)
            width, height = font.get_width_height()
            self.file._annotations[-1][1].append(_get_link_annotation(
                gc, x, y, width / 64, height / 64, angle))

        # If fonttype is neither 3 nor 42, emit the whole string at once
        # without manual kerning.
        if fonttype not in [3, 42]:
            self.file.output(Op.begin_text,
                             self.file.fontName(prop), fontsize, Op.selectfont)
            self._setup_textpos(x, y, angle)
            self.file.output(self.encode_string(s, fonttype),
                             Op.show, Op.end_text)

        # A sequence of characters is broken into multiple chunks. The chunking
        # serves two purposes:
        #   - For Type 3 fonts, there is no way to access multibyte characters,
        #     as they cannot have a CIDMap.  Therefore, in this case we break
        #     the string into chunks, where each chunk contains either a string
        #     of consecutive 1-byte characters or a single multibyte character.
        #   - A sequence of 1-byte characters is split into chunks to allow for
        #     kerning adjustments between consecutive chunks.
        #
        # Each chunk is emitted with a separate command: 1-byte characters use
        # the regular text show command (TJ) with appropriate kerning between
        # chunks, whereas multibyte characters use the XObject command (Do).
        else:
            # List of (ft_object, start_x, [prev_kern, char, char, ...]),
            # w/o zero kerns.
            singlebyte_chunks = []
            # List of (ft_object, start_x, glyph_index).
            multibyte_glyphs = []
            prev_was_multibyte = True
            prev_font = font
            for item in _text_helpers.layout(s, font, kern_mode=Kerning.UNFITTED):
                if _font_supports_glyph(fonttype, ord(item.char)):
                    if prev_was_multibyte or item.ft_object != prev_font:
                        singlebyte_chunks.append((item.ft_object, item.x, []))
                        prev_font = item.ft_object
                    if item.prev_kern:
                        singlebyte_chunks[-1][2].append(item.prev_kern)
                    singlebyte_chunks[-1][2].append(item.char)
                    prev_was_multibyte = False
                else:
                    multibyte_glyphs.append((item.ft_object, item.x, item.glyph_idx))
                    prev_was_multibyte = True
            # Do the rotation and global translation as a single matrix
            # concatenation up front
            self.file.output(Op.gsave)
            a = math.radians(angle)
            self.file.output(math.cos(a), math.sin(a),
                             -math.sin(a), math.cos(a),
                             x, y, Op.concat_matrix)
            # Emit all the 1-byte characters in a BT/ET group.

            self.file.output(Op.begin_text)
            prev_start_x = 0
            for ft_object, start_x, kerns_or_chars in singlebyte_chunks:
                ft_name = self.file.fontName(ft_object.fname)
                self.file.output(ft_name, fontsize, Op.selectfont)
                self._setup_textpos(start_x, 0, 0, prev_start_x, 0, 0)
                self.file.output(
                    # See pdf spec "Text space details" for the 1000/fontsize
                    # (aka. 1000/T_fs) factor.
                    [-1000 * next(group) / fontsize if tp == float  # a kern
                     else self.encode_string("".join(group), fonttype)
                     for tp, group in itertools.groupby(kerns_or_chars, type)],
                    Op.showkern)
                prev_start_x = start_x
            self.file.output(Op.end_text)
            # Then emit all the multibyte characters, one at a time.
            for ft_object, start_x, glyph_idx in multibyte_glyphs:
                self._draw_xobject_glyph(
                    ft_object, fontsize, glyph_idx, start_x, 0
                )
            self.file.output(Op.grestore)

    def _draw_xobject_glyph(self, font, fontsize, glyph_idx, x, y):
        """Draw a multibyte character from a Type 3 font as an XObject."""
        glyph_name = font.get_glyph_name(glyph_idx)
        name = self.file._get_xobject_glyph_name(font.fname, glyph_name)
        self.file.output(
            Op.gsave,
            0.001 * fontsize, 0, 0, 0.001 * fontsize, x, y, Op.concat_matrix,
            Name(name), Op.use_xobject,
            Op.grestore,
        )

    def new_gc(self):
        # docstring inherited
        return GraphicsContextPdf(self.file)


class GraphicsContextPdf(GraphicsContextBase):

    def __init__(self, file):
        super().__init__()
        self._fillcolor = (0.0, 0.0, 0.0)
        self._effective_alphas = (1.0, 1.0)
        self.file = file
        self.parent = None

    def __repr__(self):
        d = dict(self.__dict__)
        del d['file']
        del d['parent']
        return repr(d)

    def stroke(self):
        """
        Predicate: does the path need to be stroked (its outline drawn)?
        This tests for the various conditions that disable stroking
        the path, in which case it would presumably be filled.
        """
        # _linewidth > 0: in pdf a line of width 0 is drawn at minimum
        #   possible device width, but e.g., agg doesn't draw at all
        return (self._linewidth > 0 and self._alpha > 0 and
                (len(self._rgb) <= 3 or self._rgb[3] != 0.0))

    def fill(self, *args):
        """
        Predicate: does the path need to be filled?

        An optional argument can be used to specify an alternative
        _fillcolor, as needed by RendererPdf.draw_markers.
        """
        if len(args):
            _fillcolor = args[0]
        else:
            _fillcolor = self._fillcolor
        return (self._hatch or
                (_fillcolor is not None and
                 (len(_fillcolor) <= 3 or _fillcolor[3] != 0.0)))

    def paint(self):
        """
        Return the appropriate pdf operator to cause the path to be
        stroked, filled, or both.
        """
        return Op.paint_path(self.fill(), self.stroke())

    capstyles = {'butt': 0, 'round': 1, 'projecting': 2}
    joinstyles = {'miter': 0, 'round': 1, 'bevel': 2}

    def capstyle_cmd(self, style):
        return [self.capstyles[style], Op.setlinecap]

    def joinstyle_cmd(self, style):
        return [self.joinstyles[style], Op.setlinejoin]

    def linewidth_cmd(self, width):
        return [width, Op.setlinewidth]

    def dash_cmd(self, dashes):
        offset, dash = dashes
        if dash is None:
            dash = []
            offset = 0
        return [list(dash), offset, Op.setdash]

    def alpha_cmd(self, alpha, forced, effective_alphas):
        name = self.file.alphaState(effective_alphas)
        return [name, Op.setgstate]

    def hatch_cmd(self, hatch, hatch_color, hatch_linewidth):
        if not hatch:
            if self._fillcolor is not None:
                return self.fillcolor_cmd(self._fillcolor)
            else:
                return [Name('DeviceRGB'), Op.setcolorspace_nonstroke]
        else:
            hatch_style = (hatch_color, self._fillcolor, hatch, hatch_linewidth)
            name = self.file.hatchPattern(hatch_style)
            return [Name('Pattern'), Op.setcolorspace_nonstroke,
                    name, Op.setcolor_nonstroke]

    def rgb_cmd(self, rgb):
        if mpl.rcParams['pdf.inheritcolor']:
            return []
        if rgb[0] == rgb[1] == rgb[2]:
            return [rgb[0], Op.setgray_stroke]
        else:
            return [*rgb[:3], Op.setrgb_stroke]

    def fillcolor_cmd(self, rgb):
        if rgb is None or mpl.rcParams['pdf.inheritcolor']:
            return []
        elif rgb[0] == rgb[1] == rgb[2]:
            return [rgb[0], Op.setgray_nonstroke]
        else:
            return [*rgb[:3], Op.setrgb_nonstroke]

    def push(self):
        parent = GraphicsContextPdf(self.file)
        parent.copy_properties(self)
        parent.parent = self.parent
        self.parent = parent
        return [Op.gsave]

    def pop(self):
        assert self.parent is not None
        self.copy_properties(self.parent)
        self.parent = self.parent.parent
        return [Op.grestore]

    def clip_cmd(self, cliprect, clippath):
        """Set clip rectangle. Calls `.pop()` and `.push()`."""
        cmds = []
        # Pop graphics state until we hit the right one or the stack is empty
        while ((self._cliprect, self._clippath) != (cliprect, clippath)
                and self.parent is not None):
            cmds.extend(self.pop())
        # Unless we hit the right one, set the clip polygon
        if ((self._cliprect, self._clippath) != (cliprect, clippath) or
                self.parent is None):
            cmds.extend(self.push())
            if self._cliprect != cliprect:
                cmds.extend([cliprect, Op.rectangle, Op.clip, Op.endpath])
            if self._clippath != clippath:
                path, affine = clippath.get_transformed_path_and_affine()
                cmds.extend(
                    PdfFile.pathOperations(path, affine, simplify=False) +
                    [Op.clip, Op.endpath])
        return cmds

    commands = (
        # must come first since may pop
        (('_cliprect', '_clippath'), clip_cmd),
        (('_alpha', '_forced_alpha', '_effective_alphas'), alpha_cmd),
        (('_capstyle',), capstyle_cmd),
        (('_fillcolor',), fillcolor_cmd),
        (('_joinstyle',), joinstyle_cmd),
        (('_linewidth',), linewidth_cmd),
        (('_dashes',), dash_cmd),
        (('_rgb',), rgb_cmd),
        # must come after fillcolor and rgb
        (('_hatch', '_hatch_color', '_hatch_linewidth'), hatch_cmd),
    )

    def delta(self, other):
        """
        Copy properties of other into self and return PDF commands
        needed to transform *self* into *other*.
        """
        cmds = []
        fill_performed = False
        for params, cmd in self.commands:
            different = False
            for p in params:
                ours = getattr(self, p)
                theirs = getattr(other, p)
                try:
                    if ours is None or theirs is None:
                        different = ours is not theirs
                    else:
                        different = bool(ours != theirs)
                except ValueError:
                    ours = np.asarray(ours)
                    theirs = np.asarray(theirs)
                    different = (ours.shape != theirs.shape or
                                 np.any(ours != theirs))
                if different:
                    break

            # Need to update hatching if we also updated fillcolor
            if cmd.__name__ == 'hatch_cmd' and fill_performed:
                different = True

            if different:
                if cmd.__name__ == 'fillcolor_cmd':
                    fill_performed = True
                theirs = [getattr(other, p) for p in params]
                cmds.extend(cmd(self, *theirs))
                for p in params:
                    setattr(self, p, getattr(other, p))
        return cmds

    def copy_properties(self, other):
        """
        Copy properties of other into self.
        """
        super().copy_properties(other)
        fillcolor = getattr(other, '_fillcolor', self._fillcolor)
        effective_alphas = getattr(other, '_effective_alphas',
                                   self._effective_alphas)
        self._fillcolor = fillcolor
        self._effective_alphas = effective_alphas

    def finalize(self):
        """
        Make sure every pushed graphics state is popped.
        """
        cmds = []
        while self.parent is not None:
            cmds.extend(self.pop())
        return cmds


class PdfPages:
    """
    A multi-page PDF file.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> # Initialize:
    >>> with PdfPages('foo.pdf') as pdf:
    ...     # As many times as you like, create a figure fig and save it:
    ...     fig = plt.figure()
    ...     pdf.savefig(fig)
    ...     # When no figure is specified the current figure is saved
    ...     pdf.savefig()

    Notes
    -----
    In reality `PdfPages` is a thin wrapper around `PdfFile`, in order to avoid
    confusion when using `~.pyplot.savefig` and forgetting the format argument.
    """

    @_api.delete_parameter("3.10", "keep_empty",
                           addendum="This parameter does nothing.")
    def __init__(self, filename, keep_empty=None, metadata=None):
        """
        Create a new PdfPages object.

        Parameters
        ----------
        filename : str or path-like or file-like
            Plots using `PdfPages.savefig` will be written to a file at this location.
            The file is opened when a figure is saved for the first time (overwriting
            any older file with the same name).

        metadata : dict, optional
            Information dictionary object (see PDF reference section 10.2.1
            'Document Information Dictionary'), e.g.:
            ``{'Creator': 'My software', 'Author': 'Me', 'Title': 'Awesome'}``.

            The standard keys are 'Title', 'Author', 'Subject', 'Keywords',
            'Creator', 'Producer', 'CreationDate', 'ModDate', and
            'Trapped'. Values have been predefined for 'Creator', 'Producer'
            and 'CreationDate'. They can be removed by setting them to `None`.
        """
        self._filename = filename
        self._metadata = metadata
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _ensure_file(self):
        if self._file is None:
            self._file = PdfFile(self._filename, metadata=self._metadata)  # init.
        return self._file

    def close(self):
        """
        Finalize this object, making the underlying file a complete
        PDF file.
        """
        if self._file is not None:
            self._file.finalize()
            self._file.close()
            self._file = None

    def infodict(self):
        """
        Return a modifiable information dictionary object
        (see PDF reference section 10.2.1 'Document Information
        Dictionary').
        """
        return self._ensure_file().infoDict

    def savefig(self, figure=None, **kwargs):
        """
        Save a `.Figure` to this file as a new page.

        Any other keyword arguments are passed to `~.Figure.savefig`.

        Parameters
        ----------
        figure : `.Figure` or int, default: the active figure
            The figure, or index of the figure, that is saved to the file.
        """
        if not isinstance(figure, Figure):
            if figure is None:
                manager = Gcf.get_active()
            else:
                manager = Gcf.get_fig_manager(figure)
            if manager is None:
                raise ValueError(f"No figure {figure}")
            figure = manager.canvas.figure
        # Force use of pdf backend, as PdfPages is tightly coupled with it.
        figure.savefig(self, format="pdf", backend="pdf", **kwargs)

    def get_pagecount(self):
        """Return the current number of pages in the multipage pdf file."""
        return len(self._ensure_file().pageList)

    def attach_note(self, text, positionRect=[-100, -100, 0, 0]):
        """
        Add a new text note to the page to be saved next. The optional
        positionRect specifies the position of the new note on the
        page. It is outside the page per default to make sure it is
        invisible on printouts.
        """
        self._ensure_file().newTextnote(text, positionRect)


class FigureCanvasPdf(FigureCanvasBase):
    # docstring inherited

    fixed_dpi = 72
    filetypes = {'pdf': 'Portable Document Format'}

    def get_default_filetype(self):
        return 'pdf'

    def print_pdf(self, filename, *,
                  bbox_inches_restore=None, metadata=None):

        dpi = self.figure.dpi
        self.figure.dpi = 72  # there are 72 pdf points to an inch
        width, height = self.figure.get_size_inches()
        if isinstance(filename, PdfPages):
            file = filename._ensure_file()
        else:
            file = PdfFile(filename, metadata=metadata)
        try:
            file.newPage(width, height)
            renderer = MixedModeRenderer(
                self.figure, width, height, dpi,
                RendererPdf(file, dpi, height, width),
                bbox_inches_restore=bbox_inches_restore)
            self.figure.draw(renderer)
            renderer.finalize()
            if not isinstance(filename, PdfPages):
                file.finalize()
        finally:
            if isinstance(filename, PdfPages):  # finish off this page
                file.endStream()
            else:            # we opened the file above; now finish it off
                file.close()

    def draw(self):
        self.figure.draw_without_rendering()
        return super().draw()


FigureManagerPdf = FigureManagerBase


@_Backend.export
class _BackendPdf(_Backend):
    FigureCanvas = FigureCanvasPdf

# === NexusCore/openenv\Lib\site-packages\google\protobuf\descriptor_pb2.py ===
# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: google/protobuf/descriptor.proto
# Protobuf Python Version: 4.25.8
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR = _descriptor.FileDescriptor(
    name='google/protobuf/descriptor.proto',
    package='google.protobuf',
    syntax='proto2',
    serialized_options=b'\n\023com.google.protobufB\020DescriptorProtosH\001Z-google.golang.org/protobuf/types/descriptorpb\370\001\001\242\002\003GPB\252\002\032Google.Protobuf.Reflection',
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n google/protobuf/descriptor.proto\x12\x0fgoogle.protobuf\"M\n\x11\x46ileDescriptorSet\x12\x38\n\x04\x66ile\x18\x01 \x03(\x0b\x32$.google.protobuf.FileDescriptorProtoR\x04\x66ile\"\x98\x05\n\x13\x46ileDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x18\n\x07package\x18\x02 \x01(\tR\x07package\x12\x1e\n\ndependency\x18\x03 \x03(\tR\ndependency\x12+\n\x11public_dependency\x18\n \x03(\x05R\x10publicDependency\x12\'\n\x0fweak_dependency\x18\x0b \x03(\x05R\x0eweakDependency\x12\x43\n\x0cmessage_type\x18\x04 \x03(\x0b\x32 .google.protobuf.DescriptorProtoR\x0bmessageType\x12\x41\n\tenum_type\x18\x05 \x03(\x0b\x32$.google.protobuf.EnumDescriptorProtoR\x08\x65numType\x12\x41\n\x07service\x18\x06 \x03(\x0b\x32\'.google.protobuf.ServiceDescriptorProtoR\x07service\x12\x43\n\textension\x18\x07 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\textension\x12\x36\n\x07options\x18\x08 \x01(\x0b\x32\x1c.google.protobuf.FileOptionsR\x07options\x12I\n\x10source_code_info\x18\t \x01(\x0b\x32\x1f.google.protobuf.SourceCodeInfoR\x0esourceCodeInfo\x12\x16\n\x06syntax\x18\x0c \x01(\tR\x06syntax\x12\x32\n\x07\x65\x64ition\x18\x0e \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\"\xb9\x06\n\x0f\x44\x65scriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12;\n\x05\x66ield\x18\x02 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\x05\x66ield\x12\x43\n\textension\x18\x06 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\textension\x12\x41\n\x0bnested_type\x18\x03 \x03(\x0b\x32 .google.protobuf.DescriptorProtoR\nnestedType\x12\x41\n\tenum_type\x18\x04 \x03(\x0b\x32$.google.protobuf.EnumDescriptorProtoR\x08\x65numType\x12X\n\x0f\x65xtension_range\x18\x05 \x03(\x0b\x32/.google.protobuf.DescriptorProto.ExtensionRangeR\x0e\x65xtensionRange\x12\x44\n\noneof_decl\x18\x08 \x03(\x0b\x32%.google.protobuf.OneofDescriptorProtoR\toneofDecl\x12\x39\n\x07options\x18\x07 \x01(\x0b\x32\x1f.google.protobuf.MessageOptionsR\x07options\x12U\n\x0ereserved_range\x18\t \x03(\x0b\x32..google.protobuf.DescriptorProto.ReservedRangeR\rreservedRange\x12#\n\rreserved_name\x18\n \x03(\tR\x0creservedName\x1az\n\x0e\x45xtensionRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\x12@\n\x07options\x18\x03 \x01(\x0b\x32&.google.protobuf.ExtensionRangeOptionsR\x07options\x1a\x37\n\rReservedRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\"\xc7\x04\n\x15\x45xtensionRangeOptions\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\x12Y\n\x0b\x64\x65\x63laration\x18\x02 \x03(\x0b\x32\x32.google.protobuf.ExtensionRangeOptions.DeclarationB\x03\x88\x01\x02R\x0b\x64\x65\x63laration\x12\x37\n\x08\x66\x65\x61tures\x18\x32 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12h\n\x0cverification\x18\x03 \x01(\x0e\x32\x38.google.protobuf.ExtensionRangeOptions.VerificationState:\nUNVERIFIEDR\x0cverification\x1a\x94\x01\n\x0b\x44\x65\x63laration\x12\x16\n\x06number\x18\x01 \x01(\x05R\x06number\x12\x1b\n\tfull_name\x18\x02 \x01(\tR\x08\x66ullName\x12\x12\n\x04type\x18\x03 \x01(\tR\x04type\x12\x1a\n\x08reserved\x18\x05 \x01(\x08R\x08reserved\x12\x1a\n\x08repeated\x18\x06 \x01(\x08R\x08repeatedJ\x04\x08\x04\x10\x05\"4\n\x11VerificationState\x12\x0f\n\x0b\x44\x45\x43LARATION\x10\x00\x12\x0e\n\nUNVERIFIED\x10\x01*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xc1\x06\n\x14\x46ieldDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x16\n\x06number\x18\x03 \x01(\x05R\x06number\x12\x41\n\x05label\x18\x04 \x01(\x0e\x32+.google.protobuf.FieldDescriptorProto.LabelR\x05label\x12>\n\x04type\x18\x05 \x01(\x0e\x32*.google.protobuf.FieldDescriptorProto.TypeR\x04type\x12\x1b\n\ttype_name\x18\x06 \x01(\tR\x08typeName\x12\x1a\n\x08\x65xtendee\x18\x02 \x01(\tR\x08\x65xtendee\x12#\n\rdefault_value\x18\x07 \x01(\tR\x0c\x64\x65\x66\x61ultValue\x12\x1f\n\x0boneof_index\x18\t \x01(\x05R\noneofIndex\x12\x1b\n\tjson_name\x18\n \x01(\tR\x08jsonName\x12\x37\n\x07options\x18\x08 \x01(\x0b\x32\x1d.google.protobuf.FieldOptionsR\x07options\x12\'\n\x0fproto3_optional\x18\x11 \x01(\x08R\x0eproto3Optional\"\xb6\x02\n\x04Type\x12\x0f\n\x0bTYPE_DOUBLE\x10\x01\x12\x0e\n\nTYPE_FLOAT\x10\x02\x12\x0e\n\nTYPE_INT64\x10\x03\x12\x0f\n\x0bTYPE_UINT64\x10\x04\x12\x0e\n\nTYPE_INT32\x10\x05\x12\x10\n\x0cTYPE_FIXED64\x10\x06\x12\x10\n\x0cTYPE_FIXED32\x10\x07\x12\r\n\tTYPE_BOOL\x10\x08\x12\x0f\n\x0bTYPE_STRING\x10\t\x12\x0e\n\nTYPE_GROUP\x10\n\x12\x10\n\x0cTYPE_MESSAGE\x10\x0b\x12\x0e\n\nTYPE_BYTES\x10\x0c\x12\x0f\n\x0bTYPE_UINT32\x10\r\x12\r\n\tTYPE_ENUM\x10\x0e\x12\x11\n\rTYPE_SFIXED32\x10\x0f\x12\x11\n\rTYPE_SFIXED64\x10\x10\x12\x0f\n\x0bTYPE_SINT32\x10\x11\x12\x0f\n\x0bTYPE_SINT64\x10\x12\"C\n\x05Label\x12\x12\n\x0eLABEL_OPTIONAL\x10\x01\x12\x12\n\x0eLABEL_REPEATED\x10\x03\x12\x12\n\x0eLABEL_REQUIRED\x10\x02\"c\n\x14OneofDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x37\n\x07options\x18\x02 \x01(\x0b\x32\x1d.google.protobuf.OneofOptionsR\x07options\"\xe3\x02\n\x13\x45numDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12?\n\x05value\x18\x02 \x03(\x0b\x32).google.protobuf.EnumValueDescriptorProtoR\x05value\x12\x36\n\x07options\x18\x03 \x01(\x0b\x32\x1c.google.protobuf.EnumOptionsR\x07options\x12]\n\x0ereserved_range\x18\x04 \x03(\x0b\x32\x36.google.protobuf.EnumDescriptorProto.EnumReservedRangeR\rreservedRange\x12#\n\rreserved_name\x18\x05 \x03(\tR\x0creservedName\x1a;\n\x11\x45numReservedRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\"\x83\x01\n\x18\x45numValueDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x16\n\x06number\x18\x02 \x01(\x05R\x06number\x12;\n\x07options\x18\x03 \x01(\x0b\x32!.google.protobuf.EnumValueOptionsR\x07options\"\xa7\x01\n\x16ServiceDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12>\n\x06method\x18\x02 \x03(\x0b\x32&.google.protobuf.MethodDescriptorProtoR\x06method\x12\x39\n\x07options\x18\x03 \x01(\x0b\x32\x1f.google.protobuf.ServiceOptionsR\x07options\"\x89\x02\n\x15MethodDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x1d\n\ninput_type\x18\x02 \x01(\tR\tinputType\x12\x1f\n\x0boutput_type\x18\x03 \x01(\tR\noutputType\x12\x38\n\x07options\x18\x04 \x01(\x0b\x32\x1e.google.protobuf.MethodOptionsR\x07options\x12\x30\n\x10\x63lient_streaming\x18\x05 \x01(\x08:\x05\x66\x61lseR\x0f\x63lientStreaming\x12\x30\n\x10server_streaming\x18\x06 \x01(\x08:\x05\x66\x61lseR\x0fserverStreaming\"\xca\t\n\x0b\x46ileOptions\x12!\n\x0cjava_package\x18\x01 \x01(\tR\x0bjavaPackage\x12\x30\n\x14java_outer_classname\x18\x08 \x01(\tR\x12javaOuterClassname\x12\x35\n\x13java_multiple_files\x18\n \x01(\x08:\x05\x66\x61lseR\x11javaMultipleFiles\x12\x44\n\x1djava_generate_equals_and_hash\x18\x14 \x01(\x08\x42\x02\x18\x01R\x19javaGenerateEqualsAndHash\x12:\n\x16java_string_check_utf8\x18\x1b \x01(\x08:\x05\x66\x61lseR\x13javaStringCheckUtf8\x12S\n\x0coptimize_for\x18\t \x01(\x0e\x32).google.protobuf.FileOptions.OptimizeMode:\x05SPEEDR\x0boptimizeFor\x12\x1d\n\ngo_package\x18\x0b \x01(\tR\tgoPackage\x12\x35\n\x13\x63\x63_generic_services\x18\x10 \x01(\x08:\x05\x66\x61lseR\x11\x63\x63GenericServices\x12\x39\n\x15java_generic_services\x18\x11 \x01(\x08:\x05\x66\x61lseR\x13javaGenericServices\x12\x35\n\x13py_generic_services\x18\x12 \x01(\x08:\x05\x66\x61lseR\x11pyGenericServices\x12\x37\n\x14php_generic_services\x18* \x01(\x08:\x05\x66\x61lseR\x12phpGenericServices\x12%\n\ndeprecated\x18\x17 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12.\n\x10\x63\x63_enable_arenas\x18\x1f \x01(\x08:\x04trueR\x0e\x63\x63\x45nableArenas\x12*\n\x11objc_class_prefix\x18$ \x01(\tR\x0fobjcClassPrefix\x12)\n\x10\x63sharp_namespace\x18% \x01(\tR\x0f\x63sharpNamespace\x12!\n\x0cswift_prefix\x18\' \x01(\tR\x0bswiftPrefix\x12(\n\x10php_class_prefix\x18( \x01(\tR\x0ephpClassPrefix\x12#\n\rphp_namespace\x18) \x01(\tR\x0cphpNamespace\x12\x34\n\x16php_metadata_namespace\x18, \x01(\tR\x14phpMetadataNamespace\x12!\n\x0cruby_package\x18- \x01(\tR\x0brubyPackage\x12\x37\n\x08\x66\x65\x61tures\x18\x32 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\":\n\x0cOptimizeMode\x12\t\n\x05SPEED\x10\x01\x12\r\n\tCODE_SIZE\x10\x02\x12\x10\n\x0cLITE_RUNTIME\x10\x03*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08&\x10\'\"\xf4\x03\n\x0eMessageOptions\x12<\n\x17message_set_wire_format\x18\x01 \x01(\x08:\x05\x66\x61lseR\x14messageSetWireFormat\x12L\n\x1fno_standard_descriptor_accessor\x18\x02 \x01(\x08:\x05\x66\x61lseR\x1cnoStandardDescriptorAccessor\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x1b\n\tmap_entry\x18\x07 \x01(\x08R\x08mapEntry\x12V\n&deprecated_legacy_json_field_conflicts\x18\x0b \x01(\x08\x42\x02\x18\x01R\"deprecatedLegacyJsonFieldConflicts\x12\x37\n\x08\x66\x65\x61tures\x18\x0c \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x04\x10\x05J\x04\x08\x05\x10\x06J\x04\x08\x06\x10\x07J\x04\x08\x08\x10\tJ\x04\x08\t\x10\n\"\xad\n\n\x0c\x46ieldOptions\x12\x41\n\x05\x63type\x18\x01 \x01(\x0e\x32#.google.protobuf.FieldOptions.CType:\x06STRINGR\x05\x63type\x12\x16\n\x06packed\x18\x02 \x01(\x08R\x06packed\x12G\n\x06jstype\x18\x06 \x01(\x0e\x32$.google.protobuf.FieldOptions.JSType:\tJS_NORMALR\x06jstype\x12\x19\n\x04lazy\x18\x05 \x01(\x08:\x05\x66\x61lseR\x04lazy\x12.\n\x0funverified_lazy\x18\x0f \x01(\x08:\x05\x66\x61lseR\x0eunverifiedLazy\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x19\n\x04weak\x18\n \x01(\x08:\x05\x66\x61lseR\x04weak\x12(\n\x0c\x64\x65\x62ug_redact\x18\x10 \x01(\x08:\x05\x66\x61lseR\x0b\x64\x65\x62ugRedact\x12K\n\tretention\x18\x11 \x01(\x0e\x32-.google.protobuf.FieldOptions.OptionRetentionR\tretention\x12H\n\x07targets\x18\x13 \x03(\x0e\x32..google.protobuf.FieldOptions.OptionTargetTypeR\x07targets\x12W\n\x10\x65\x64ition_defaults\x18\x14 \x03(\x0b\x32,.google.protobuf.FieldOptions.EditionDefaultR\x0f\x65\x64itionDefaults\x12\x37\n\x08\x66\x65\x61tures\x18\x15 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\x1aZ\n\x0e\x45\x64itionDefault\x12\x32\n\x07\x65\x64ition\x18\x03 \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\x12\x14\n\x05value\x18\x02 \x01(\tR\x05value\"/\n\x05\x43Type\x12\n\n\x06STRING\x10\x00\x12\x08\n\x04\x43ORD\x10\x01\x12\x10\n\x0cSTRING_PIECE\x10\x02\"5\n\x06JSType\x12\r\n\tJS_NORMAL\x10\x00\x12\r\n\tJS_STRING\x10\x01\x12\r\n\tJS_NUMBER\x10\x02\"U\n\x0fOptionRetention\x12\x15\n\x11RETENTION_UNKNOWN\x10\x00\x12\x15\n\x11RETENTION_RUNTIME\x10\x01\x12\x14\n\x10RETENTION_SOURCE\x10\x02\"\x8c\x02\n\x10OptionTargetType\x12\x17\n\x13TARGET_TYPE_UNKNOWN\x10\x00\x12\x14\n\x10TARGET_TYPE_FILE\x10\x01\x12\x1f\n\x1bTARGET_TYPE_EXTENSION_RANGE\x10\x02\x12\x17\n\x13TARGET_TYPE_MESSAGE\x10\x03\x12\x15\n\x11TARGET_TYPE_FIELD\x10\x04\x12\x15\n\x11TARGET_TYPE_ONEOF\x10\x05\x12\x14\n\x10TARGET_TYPE_ENUM\x10\x06\x12\x1a\n\x16TARGET_TYPE_ENUM_ENTRY\x10\x07\x12\x17\n\x13TARGET_TYPE_SERVICE\x10\x08\x12\x16\n\x12TARGET_TYPE_METHOD\x10\t*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x04\x10\x05J\x04\x08\x12\x10\x13\"\xac\x01\n\x0cOneofOptions\x12\x37\n\x08\x66\x65\x61tures\x18\x01 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xd1\x02\n\x0b\x45numOptions\x12\x1f\n\x0b\x61llow_alias\x18\x02 \x01(\x08R\nallowAlias\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12V\n&deprecated_legacy_json_field_conflicts\x18\x06 \x01(\x08\x42\x02\x18\x01R\"deprecatedLegacyJsonFieldConflicts\x12\x37\n\x08\x66\x65\x61tures\x18\x07 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x05\x10\x06\"\x81\x02\n\x10\x45numValueOptions\x12%\n\ndeprecated\x18\x01 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x37\n\x08\x66\x65\x61tures\x18\x02 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12(\n\x0c\x64\x65\x62ug_redact\x18\x03 \x01(\x08:\x05\x66\x61lseR\x0b\x64\x65\x62ugRedact\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xd5\x01\n\x0eServiceOptions\x12\x37\n\x08\x66\x65\x61tures\x18\" \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12%\n\ndeprecated\x18! \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\x99\x03\n\rMethodOptions\x12%\n\ndeprecated\x18! \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12q\n\x11idempotency_level\x18\" \x01(\x0e\x32/.google.protobuf.MethodOptions.IdempotencyLevel:\x13IDEMPOTENCY_UNKNOWNR\x10idempotencyLevel\x12\x37\n\x08\x66\x65\x61tures\x18# \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\"P\n\x10IdempotencyLevel\x12\x17\n\x13IDEMPOTENCY_UNKNOWN\x10\x00\x12\x13\n\x0fNO_SIDE_EFFECTS\x10\x01\x12\x0e\n\nIDEMPOTENT\x10\x02*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\x9a\x03\n\x13UninterpretedOption\x12\x41\n\x04name\x18\x02 \x03(\x0b\x32-.google.protobuf.UninterpretedOption.NamePartR\x04name\x12)\n\x10identifier_value\x18\x03 \x01(\tR\x0fidentifierValue\x12,\n\x12positive_int_value\x18\x04 \x01(\x04R\x10positiveIntValue\x12,\n\x12negative_int_value\x18\x05 \x01(\x03R\x10negativeIntValue\x12!\n\x0c\x64ouble_value\x18\x06 \x01(\x01R\x0b\x64oubleValue\x12!\n\x0cstring_value\x18\x07 \x01(\x0cR\x0bstringValue\x12\'\n\x0f\x61ggregate_value\x18\x08 \x01(\tR\x0e\x61ggregateValue\x1aJ\n\x08NamePart\x12\x1b\n\tname_part\x18\x01 \x02(\tR\x08namePart\x12!\n\x0cis_extension\x18\x02 \x02(\x08R\x0bisExtension\"\xfc\t\n\nFeatureSet\x12\x8b\x01\n\x0e\x66ield_presence\x18\x01 \x01(\x0e\x32).google.protobuf.FeatureSet.FieldPresenceB9\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\r\x12\x08\x45XPLICIT\x18\xe6\x07\xa2\x01\r\x12\x08IMPLICIT\x18\xe7\x07\xa2\x01\r\x12\x08\x45XPLICIT\x18\xe8\x07R\rfieldPresence\x12\x66\n\tenum_type\x18\x02 \x01(\x0e\x32$.google.protobuf.FeatureSet.EnumTypeB#\x88\x01\x01\x98\x01\x06\x98\x01\x01\xa2\x01\x0b\x12\x06\x43LOSED\x18\xe6\x07\xa2\x01\t\x12\x04OPEN\x18\xe7\x07R\x08\x65numType\x12\x92\x01\n\x17repeated_field_encoding\x18\x03 \x01(\x0e\x32\x31.google.protobuf.FeatureSet.RepeatedFieldEncodingB\'\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\r\x12\x08\x45XPANDED\x18\xe6\x07\xa2\x01\x0b\x12\x06PACKED\x18\xe7\x07R\x15repeatedFieldEncoding\x12x\n\x0futf8_validation\x18\x04 \x01(\x0e\x32*.google.protobuf.FeatureSet.Utf8ValidationB#\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\t\x12\x04NONE\x18\xe6\x07\xa2\x01\x0b\x12\x06VERIFY\x18\xe7\x07R\x0eutf8Validation\x12x\n\x10message_encoding\x18\x05 \x01(\x0e\x32+.google.protobuf.FeatureSet.MessageEncodingB \x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\x14\x12\x0fLENGTH_PREFIXED\x18\xe6\x07R\x0fmessageEncoding\x12|\n\x0bjson_format\x18\x06 \x01(\x0e\x32&.google.protobuf.FeatureSet.JsonFormatB3\x88\x01\x01\x98\x01\x03\x98\x01\x06\x98\x01\x01\xa2\x01\x17\x12\x12LEGACY_BEST_EFFORT\x18\xe6\x07\xa2\x01\n\x12\x05\x41LLOW\x18\xe7\x07R\njsonFormat\"\\\n\rFieldPresence\x12\x1a\n\x16\x46IELD_PRESENCE_UNKNOWN\x10\x00\x12\x0c\n\x08\x45XPLICIT\x10\x01\x12\x0c\n\x08IMPLICIT\x10\x02\x12\x13\n\x0fLEGACY_REQUIRED\x10\x03\"7\n\x08\x45numType\x12\x15\n\x11\x45NUM_TYPE_UNKNOWN\x10\x00\x12\x08\n\x04OPEN\x10\x01\x12\n\n\x06\x43LOSED\x10\x02\"V\n\x15RepeatedFieldEncoding\x12#\n\x1fREPEATED_FIELD_ENCODING_UNKNOWN\x10\x00\x12\n\n\x06PACKED\x10\x01\x12\x0c\n\x08\x45XPANDED\x10\x02\"C\n\x0eUtf8Validation\x12\x1b\n\x17UTF8_VALIDATION_UNKNOWN\x10\x00\x12\x08\n\x04NONE\x10\x01\x12\n\n\x06VERIFY\x10\x02\"S\n\x0fMessageEncoding\x12\x1c\n\x18MESSAGE_ENCODING_UNKNOWN\x10\x00\x12\x13\n\x0fLENGTH_PREFIXED\x10\x01\x12\r\n\tDELIMITED\x10\x02\"H\n\nJsonFormat\x12\x17\n\x13JSON_FORMAT_UNKNOWN\x10\x00\x12\t\n\x05\x41LLOW\x10\x01\x12\x16\n\x12LEGACY_BEST_EFFORT\x10\x02*\x06\x08\xe8\x07\x10\xe9\x07*\x06\x08\xe9\x07\x10\xea\x07*\x06\x08\x8bN\x10\x90NJ\x06\x08\xe7\x07\x10\xe8\x07\"\xfe\x02\n\x12\x46\x65\x61tureSetDefaults\x12X\n\x08\x64\x65\x66\x61ults\x18\x01 \x03(\x0b\x32<.google.protobuf.FeatureSetDefaults.FeatureSetEditionDefaultR\x08\x64\x65\x66\x61ults\x12\x41\n\x0fminimum_edition\x18\x04 \x01(\x0e\x32\x18.google.protobuf.EditionR\x0eminimumEdition\x12\x41\n\x0fmaximum_edition\x18\x05 \x01(\x0e\x32\x18.google.protobuf.EditionR\x0emaximumEdition\x1a\x87\x01\n\x18\x46\x65\x61tureSetEditionDefault\x12\x32\n\x07\x65\x64ition\x18\x03 \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\x12\x37\n\x08\x66\x65\x61tures\x18\x02 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\"\xa7\x02\n\x0eSourceCodeInfo\x12\x44\n\x08location\x18\x01 \x03(\x0b\x32(.google.protobuf.SourceCodeInfo.LocationR\x08location\x1a\xce\x01\n\x08Location\x12\x16\n\x04path\x18\x01 \x03(\x05\x42\x02\x10\x01R\x04path\x12\x16\n\x04span\x18\x02 \x03(\x05\x42\x02\x10\x01R\x04span\x12)\n\x10leading_comments\x18\x03 \x01(\tR\x0fleadingComments\x12+\n\x11trailing_comments\x18\x04 \x01(\tR\x10trailingComments\x12:\n\x19leading_detached_comments\x18\x06 \x03(\tR\x17leadingDetachedComments\"\xd0\x02\n\x11GeneratedCodeInfo\x12M\n\nannotation\x18\x01 \x03(\x0b\x32-.google.protobuf.GeneratedCodeInfo.AnnotationR\nannotation\x1a\xeb\x01\n\nAnnotation\x12\x16\n\x04path\x18\x01 \x03(\x05\x42\x02\x10\x01R\x04path\x12\x1f\n\x0bsource_file\x18\x02 \x01(\tR\nsourceFile\x12\x14\n\x05\x62\x65gin\x18\x03 \x01(\x05R\x05\x62\x65gin\x12\x10\n\x03\x65nd\x18\x04 \x01(\x05R\x03\x65nd\x12R\n\x08semantic\x18\x05 \x01(\x0e\x32\x36.google.protobuf.GeneratedCodeInfo.Annotation.SemanticR\x08semantic\"(\n\x08Semantic\x12\x08\n\x04NONE\x10\x00\x12\x07\n\x03SET\x10\x01\x12\t\n\x05\x41LIAS\x10\x02*\xea\x01\n\x07\x45\x64ition\x12\x13\n\x0f\x45\x44ITION_UNKNOWN\x10\x00\x12\x13\n\x0e\x45\x44ITION_PROTO2\x10\xe6\x07\x12\x13\n\x0e\x45\x44ITION_PROTO3\x10\xe7\x07\x12\x11\n\x0c\x45\x44ITION_2023\x10\xe8\x07\x12\x17\n\x13\x45\x44ITION_1_TEST_ONLY\x10\x01\x12\x17\n\x13\x45\x44ITION_2_TEST_ONLY\x10\x02\x12\x1d\n\x17\x45\x44ITION_99997_TEST_ONLY\x10\x9d\x8d\x06\x12\x1d\n\x17\x45\x44ITION_99998_TEST_ONLY\x10\x9e\x8d\x06\x12\x1d\n\x17\x45\x44ITION_99999_TEST_ONLY\x10\x9f\x8d\x06\x42~\n\x13\x63om.google.protobufB\x10\x44\x65scriptorProtosH\x01Z-google.golang.org/protobuf/types/descriptorpb\xf8\x01\x01\xa2\x02\x03GPB\xaa\x02\x1aGoogle.Protobuf.Reflection'
  )
else:
  DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n google/protobuf/descriptor.proto\x12\x0fgoogle.protobuf\"M\n\x11\x46ileDescriptorSet\x12\x38\n\x04\x66ile\x18\x01 \x03(\x0b\x32$.google.protobuf.FileDescriptorProtoR\x04\x66ile\"\x98\x05\n\x13\x46ileDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x18\n\x07package\x18\x02 \x01(\tR\x07package\x12\x1e\n\ndependency\x18\x03 \x03(\tR\ndependency\x12+\n\x11public_dependency\x18\n \x03(\x05R\x10publicDependency\x12\'\n\x0fweak_dependency\x18\x0b \x03(\x05R\x0eweakDependency\x12\x43\n\x0cmessage_type\x18\x04 \x03(\x0b\x32 .google.protobuf.DescriptorProtoR\x0bmessageType\x12\x41\n\tenum_type\x18\x05 \x03(\x0b\x32$.google.protobuf.EnumDescriptorProtoR\x08\x65numType\x12\x41\n\x07service\x18\x06 \x03(\x0b\x32\'.google.protobuf.ServiceDescriptorProtoR\x07service\x12\x43\n\textension\x18\x07 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\textension\x12\x36\n\x07options\x18\x08 \x01(\x0b\x32\x1c.google.protobuf.FileOptionsR\x07options\x12I\n\x10source_code_info\x18\t \x01(\x0b\x32\x1f.google.protobuf.SourceCodeInfoR\x0esourceCodeInfo\x12\x16\n\x06syntax\x18\x0c \x01(\tR\x06syntax\x12\x32\n\x07\x65\x64ition\x18\x0e \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\"\xb9\x06\n\x0f\x44\x65scriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12;\n\x05\x66ield\x18\x02 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\x05\x66ield\x12\x43\n\textension\x18\x06 \x03(\x0b\x32%.google.protobuf.FieldDescriptorProtoR\textension\x12\x41\n\x0bnested_type\x18\x03 \x03(\x0b\x32 .google.protobuf.DescriptorProtoR\nnestedType\x12\x41\n\tenum_type\x18\x04 \x03(\x0b\x32$.google.protobuf.EnumDescriptorProtoR\x08\x65numType\x12X\n\x0f\x65xtension_range\x18\x05 \x03(\x0b\x32/.google.protobuf.DescriptorProto.ExtensionRangeR\x0e\x65xtensionRange\x12\x44\n\noneof_decl\x18\x08 \x03(\x0b\x32%.google.protobuf.OneofDescriptorProtoR\toneofDecl\x12\x39\n\x07options\x18\x07 \x01(\x0b\x32\x1f.google.protobuf.MessageOptionsR\x07options\x12U\n\x0ereserved_range\x18\t \x03(\x0b\x32..google.protobuf.DescriptorProto.ReservedRangeR\rreservedRange\x12#\n\rreserved_name\x18\n \x03(\tR\x0creservedName\x1az\n\x0e\x45xtensionRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\x12@\n\x07options\x18\x03 \x01(\x0b\x32&.google.protobuf.ExtensionRangeOptionsR\x07options\x1a\x37\n\rReservedRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\"\xc7\x04\n\x15\x45xtensionRangeOptions\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\x12Y\n\x0b\x64\x65\x63laration\x18\x02 \x03(\x0b\x32\x32.google.protobuf.ExtensionRangeOptions.DeclarationB\x03\x88\x01\x02R\x0b\x64\x65\x63laration\x12\x37\n\x08\x66\x65\x61tures\x18\x32 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12h\n\x0cverification\x18\x03 \x01(\x0e\x32\x38.google.protobuf.ExtensionRangeOptions.VerificationState:\nUNVERIFIEDR\x0cverification\x1a\x94\x01\n\x0b\x44\x65\x63laration\x12\x16\n\x06number\x18\x01 \x01(\x05R\x06number\x12\x1b\n\tfull_name\x18\x02 \x01(\tR\x08\x66ullName\x12\x12\n\x04type\x18\x03 \x01(\tR\x04type\x12\x1a\n\x08reserved\x18\x05 \x01(\x08R\x08reserved\x12\x1a\n\x08repeated\x18\x06 \x01(\x08R\x08repeatedJ\x04\x08\x04\x10\x05\"4\n\x11VerificationState\x12\x0f\n\x0b\x44\x45\x43LARATION\x10\x00\x12\x0e\n\nUNVERIFIED\x10\x01*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xc1\x06\n\x14\x46ieldDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x16\n\x06number\x18\x03 \x01(\x05R\x06number\x12\x41\n\x05label\x18\x04 \x01(\x0e\x32+.google.protobuf.FieldDescriptorProto.LabelR\x05label\x12>\n\x04type\x18\x05 \x01(\x0e\x32*.google.protobuf.FieldDescriptorProto.TypeR\x04type\x12\x1b\n\ttype_name\x18\x06 \x01(\tR\x08typeName\x12\x1a\n\x08\x65xtendee\x18\x02 \x01(\tR\x08\x65xtendee\x12#\n\rdefault_value\x18\x07 \x01(\tR\x0c\x64\x65\x66\x61ultValue\x12\x1f\n\x0boneof_index\x18\t \x01(\x05R\noneofIndex\x12\x1b\n\tjson_name\x18\n \x01(\tR\x08jsonName\x12\x37\n\x07options\x18\x08 \x01(\x0b\x32\x1d.google.protobuf.FieldOptionsR\x07options\x12\'\n\x0fproto3_optional\x18\x11 \x01(\x08R\x0eproto3Optional\"\xb6\x02\n\x04Type\x12\x0f\n\x0bTYPE_DOUBLE\x10\x01\x12\x0e\n\nTYPE_FLOAT\x10\x02\x12\x0e\n\nTYPE_INT64\x10\x03\x12\x0f\n\x0bTYPE_UINT64\x10\x04\x12\x0e\n\nTYPE_INT32\x10\x05\x12\x10\n\x0cTYPE_FIXED64\x10\x06\x12\x10\n\x0cTYPE_FIXED32\x10\x07\x12\r\n\tTYPE_BOOL\x10\x08\x12\x0f\n\x0bTYPE_STRING\x10\t\x12\x0e\n\nTYPE_GROUP\x10\n\x12\x10\n\x0cTYPE_MESSAGE\x10\x0b\x12\x0e\n\nTYPE_BYTES\x10\x0c\x12\x0f\n\x0bTYPE_UINT32\x10\r\x12\r\n\tTYPE_ENUM\x10\x0e\x12\x11\n\rTYPE_SFIXED32\x10\x0f\x12\x11\n\rTYPE_SFIXED64\x10\x10\x12\x0f\n\x0bTYPE_SINT32\x10\x11\x12\x0f\n\x0bTYPE_SINT64\x10\x12\"C\n\x05Label\x12\x12\n\x0eLABEL_OPTIONAL\x10\x01\x12\x12\n\x0eLABEL_REPEATED\x10\x03\x12\x12\n\x0eLABEL_REQUIRED\x10\x02\"c\n\x14OneofDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x37\n\x07options\x18\x02 \x01(\x0b\x32\x1d.google.protobuf.OneofOptionsR\x07options\"\xe3\x02\n\x13\x45numDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12?\n\x05value\x18\x02 \x03(\x0b\x32).google.protobuf.EnumValueDescriptorProtoR\x05value\x12\x36\n\x07options\x18\x03 \x01(\x0b\x32\x1c.google.protobuf.EnumOptionsR\x07options\x12]\n\x0ereserved_range\x18\x04 \x03(\x0b\x32\x36.google.protobuf.EnumDescriptorProto.EnumReservedRangeR\rreservedRange\x12#\n\rreserved_name\x18\x05 \x03(\tR\x0creservedName\x1a;\n\x11\x45numReservedRange\x12\x14\n\x05start\x18\x01 \x01(\x05R\x05start\x12\x10\n\x03\x65nd\x18\x02 \x01(\x05R\x03\x65nd\"\x83\x01\n\x18\x45numValueDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x16\n\x06number\x18\x02 \x01(\x05R\x06number\x12;\n\x07options\x18\x03 \x01(\x0b\x32!.google.protobuf.EnumValueOptionsR\x07options\"\xa7\x01\n\x16ServiceDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12>\n\x06method\x18\x02 \x03(\x0b\x32&.google.protobuf.MethodDescriptorProtoR\x06method\x12\x39\n\x07options\x18\x03 \x01(\x0b\x32\x1f.google.protobuf.ServiceOptionsR\x07options\"\x89\x02\n\x15MethodDescriptorProto\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x1d\n\ninput_type\x18\x02 \x01(\tR\tinputType\x12\x1f\n\x0boutput_type\x18\x03 \x01(\tR\noutputType\x12\x38\n\x07options\x18\x04 \x01(\x0b\x32\x1e.google.protobuf.MethodOptionsR\x07options\x12\x30\n\x10\x63lient_streaming\x18\x05 \x01(\x08:\x05\x66\x61lseR\x0f\x63lientStreaming\x12\x30\n\x10server_streaming\x18\x06 \x01(\x08:\x05\x66\x61lseR\x0fserverStreaming\"\xca\t\n\x0b\x46ileOptions\x12!\n\x0cjava_package\x18\x01 \x01(\tR\x0bjavaPackage\x12\x30\n\x14java_outer_classname\x18\x08 \x01(\tR\x12javaOuterClassname\x12\x35\n\x13java_multiple_files\x18\n \x01(\x08:\x05\x66\x61lseR\x11javaMultipleFiles\x12\x44\n\x1djava_generate_equals_and_hash\x18\x14 \x01(\x08\x42\x02\x18\x01R\x19javaGenerateEqualsAndHash\x12:\n\x16java_string_check_utf8\x18\x1b \x01(\x08:\x05\x66\x61lseR\x13javaStringCheckUtf8\x12S\n\x0coptimize_for\x18\t \x01(\x0e\x32).google.protobuf.FileOptions.OptimizeMode:\x05SPEEDR\x0boptimizeFor\x12\x1d\n\ngo_package\x18\x0b \x01(\tR\tgoPackage\x12\x35\n\x13\x63\x63_generic_services\x18\x10 \x01(\x08:\x05\x66\x61lseR\x11\x63\x63GenericServices\x12\x39\n\x15java_generic_services\x18\x11 \x01(\x08:\x05\x66\x61lseR\x13javaGenericServices\x12\x35\n\x13py_generic_services\x18\x12 \x01(\x08:\x05\x66\x61lseR\x11pyGenericServices\x12\x37\n\x14php_generic_services\x18* \x01(\x08:\x05\x66\x61lseR\x12phpGenericServices\x12%\n\ndeprecated\x18\x17 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12.\n\x10\x63\x63_enable_arenas\x18\x1f \x01(\x08:\x04trueR\x0e\x63\x63\x45nableArenas\x12*\n\x11objc_class_prefix\x18$ \x01(\tR\x0fobjcClassPrefix\x12)\n\x10\x63sharp_namespace\x18% \x01(\tR\x0f\x63sharpNamespace\x12!\n\x0cswift_prefix\x18\' \x01(\tR\x0bswiftPrefix\x12(\n\x10php_class_prefix\x18( \x01(\tR\x0ephpClassPrefix\x12#\n\rphp_namespace\x18) \x01(\tR\x0cphpNamespace\x12\x34\n\x16php_metadata_namespace\x18, \x01(\tR\x14phpMetadataNamespace\x12!\n\x0cruby_package\x18- \x01(\tR\x0brubyPackage\x12\x37\n\x08\x66\x65\x61tures\x18\x32 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\":\n\x0cOptimizeMode\x12\t\n\x05SPEED\x10\x01\x12\r\n\tCODE_SIZE\x10\x02\x12\x10\n\x0cLITE_RUNTIME\x10\x03*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08&\x10\'\"\xf4\x03\n\x0eMessageOptions\x12<\n\x17message_set_wire_format\x18\x01 \x01(\x08:\x05\x66\x61lseR\x14messageSetWireFormat\x12L\n\x1fno_standard_descriptor_accessor\x18\x02 \x01(\x08:\x05\x66\x61lseR\x1cnoStandardDescriptorAccessor\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x1b\n\tmap_entry\x18\x07 \x01(\x08R\x08mapEntry\x12V\n&deprecated_legacy_json_field_conflicts\x18\x0b \x01(\x08\x42\x02\x18\x01R\"deprecatedLegacyJsonFieldConflicts\x12\x37\n\x08\x66\x65\x61tures\x18\x0c \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x04\x10\x05J\x04\x08\x05\x10\x06J\x04\x08\x06\x10\x07J\x04\x08\x08\x10\tJ\x04\x08\t\x10\n\"\xad\n\n\x0c\x46ieldOptions\x12\x41\n\x05\x63type\x18\x01 \x01(\x0e\x32#.google.protobuf.FieldOptions.CType:\x06STRINGR\x05\x63type\x12\x16\n\x06packed\x18\x02 \x01(\x08R\x06packed\x12G\n\x06jstype\x18\x06 \x01(\x0e\x32$.google.protobuf.FieldOptions.JSType:\tJS_NORMALR\x06jstype\x12\x19\n\x04lazy\x18\x05 \x01(\x08:\x05\x66\x61lseR\x04lazy\x12.\n\x0funverified_lazy\x18\x0f \x01(\x08:\x05\x66\x61lseR\x0eunverifiedLazy\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x19\n\x04weak\x18\n \x01(\x08:\x05\x66\x61lseR\x04weak\x12(\n\x0c\x64\x65\x62ug_redact\x18\x10 \x01(\x08:\x05\x66\x61lseR\x0b\x64\x65\x62ugRedact\x12K\n\tretention\x18\x11 \x01(\x0e\x32-.google.protobuf.FieldOptions.OptionRetentionR\tretention\x12H\n\x07targets\x18\x13 \x03(\x0e\x32..google.protobuf.FieldOptions.OptionTargetTypeR\x07targets\x12W\n\x10\x65\x64ition_defaults\x18\x14 \x03(\x0b\x32,.google.protobuf.FieldOptions.EditionDefaultR\x0f\x65\x64itionDefaults\x12\x37\n\x08\x66\x65\x61tures\x18\x15 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\x1aZ\n\x0e\x45\x64itionDefault\x12\x32\n\x07\x65\x64ition\x18\x03 \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\x12\x14\n\x05value\x18\x02 \x01(\tR\x05value\"/\n\x05\x43Type\x12\n\n\x06STRING\x10\x00\x12\x08\n\x04\x43ORD\x10\x01\x12\x10\n\x0cSTRING_PIECE\x10\x02\"5\n\x06JSType\x12\r\n\tJS_NORMAL\x10\x00\x12\r\n\tJS_STRING\x10\x01\x12\r\n\tJS_NUMBER\x10\x02\"U\n\x0fOptionRetention\x12\x15\n\x11RETENTION_UNKNOWN\x10\x00\x12\x15\n\x11RETENTION_RUNTIME\x10\x01\x12\x14\n\x10RETENTION_SOURCE\x10\x02\"\x8c\x02\n\x10OptionTargetType\x12\x17\n\x13TARGET_TYPE_UNKNOWN\x10\x00\x12\x14\n\x10TARGET_TYPE_FILE\x10\x01\x12\x1f\n\x1bTARGET_TYPE_EXTENSION_RANGE\x10\x02\x12\x17\n\x13TARGET_TYPE_MESSAGE\x10\x03\x12\x15\n\x11TARGET_TYPE_FIELD\x10\x04\x12\x15\n\x11TARGET_TYPE_ONEOF\x10\x05\x12\x14\n\x10TARGET_TYPE_ENUM\x10\x06\x12\x1a\n\x16TARGET_TYPE_ENUM_ENTRY\x10\x07\x12\x17\n\x13TARGET_TYPE_SERVICE\x10\x08\x12\x16\n\x12TARGET_TYPE_METHOD\x10\t*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x04\x10\x05J\x04\x08\x12\x10\x13\"\xac\x01\n\x0cOneofOptions\x12\x37\n\x08\x66\x65\x61tures\x18\x01 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xd1\x02\n\x0b\x45numOptions\x12\x1f\n\x0b\x61llow_alias\x18\x02 \x01(\x08R\nallowAlias\x12%\n\ndeprecated\x18\x03 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12V\n&deprecated_legacy_json_field_conflicts\x18\x06 \x01(\x08\x42\x02\x18\x01R\"deprecatedLegacyJsonFieldConflicts\x12\x37\n\x08\x66\x65\x61tures\x18\x07 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02J\x04\x08\x05\x10\x06\"\x81\x02\n\x10\x45numValueOptions\x12%\n\ndeprecated\x18\x01 \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12\x37\n\x08\x66\x65\x61tures\x18\x02 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12(\n\x0c\x64\x65\x62ug_redact\x18\x03 \x01(\x08:\x05\x66\x61lseR\x0b\x64\x65\x62ugRedact\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\xd5\x01\n\x0eServiceOptions\x12\x37\n\x08\x66\x65\x61tures\x18\" \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12%\n\ndeprecated\x18! \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\x99\x03\n\rMethodOptions\x12%\n\ndeprecated\x18! \x01(\x08:\x05\x66\x61lseR\ndeprecated\x12q\n\x11idempotency_level\x18\" \x01(\x0e\x32/.google.protobuf.MethodOptions.IdempotencyLevel:\x13IDEMPOTENCY_UNKNOWNR\x10idempotencyLevel\x12\x37\n\x08\x66\x65\x61tures\x18# \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\x12X\n\x14uninterpreted_option\x18\xe7\x07 \x03(\x0b\x32$.google.protobuf.UninterpretedOptionR\x13uninterpretedOption\"P\n\x10IdempotencyLevel\x12\x17\n\x13IDEMPOTENCY_UNKNOWN\x10\x00\x12\x13\n\x0fNO_SIDE_EFFECTS\x10\x01\x12\x0e\n\nIDEMPOTENT\x10\x02*\t\x08\xe8\x07\x10\x80\x80\x80\x80\x02\"\x9a\x03\n\x13UninterpretedOption\x12\x41\n\x04name\x18\x02 \x03(\x0b\x32-.google.protobuf.UninterpretedOption.NamePartR\x04name\x12)\n\x10identifier_value\x18\x03 \x01(\tR\x0fidentifierValue\x12,\n\x12positive_int_value\x18\x04 \x01(\x04R\x10positiveIntValue\x12,\n\x12negative_int_value\x18\x05 \x01(\x03R\x10negativeIntValue\x12!\n\x0c\x64ouble_value\x18\x06 \x01(\x01R\x0b\x64oubleValue\x12!\n\x0cstring_value\x18\x07 \x01(\x0cR\x0bstringValue\x12\'\n\x0f\x61ggregate_value\x18\x08 \x01(\tR\x0e\x61ggregateValue\x1aJ\n\x08NamePart\x12\x1b\n\tname_part\x18\x01 \x02(\tR\x08namePart\x12!\n\x0cis_extension\x18\x02 \x02(\x08R\x0bisExtension\"\xfc\t\n\nFeatureSet\x12\x8b\x01\n\x0e\x66ield_presence\x18\x01 \x01(\x0e\x32).google.protobuf.FeatureSet.FieldPresenceB9\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\r\x12\x08\x45XPLICIT\x18\xe6\x07\xa2\x01\r\x12\x08IMPLICIT\x18\xe7\x07\xa2\x01\r\x12\x08\x45XPLICIT\x18\xe8\x07R\rfieldPresence\x12\x66\n\tenum_type\x18\x02 \x01(\x0e\x32$.google.protobuf.FeatureSet.EnumTypeB#\x88\x01\x01\x98\x01\x06\x98\x01\x01\xa2\x01\x0b\x12\x06\x43LOSED\x18\xe6\x07\xa2\x01\t\x12\x04OPEN\x18\xe7\x07R\x08\x65numType\x12\x92\x01\n\x17repeated_field_encoding\x18\x03 \x01(\x0e\x32\x31.google.protobuf.FeatureSet.RepeatedFieldEncodingB\'\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\r\x12\x08\x45XPANDED\x18\xe6\x07\xa2\x01\x0b\x12\x06PACKED\x18\xe7\x07R\x15repeatedFieldEncoding\x12x\n\x0futf8_validation\x18\x04 \x01(\x0e\x32*.google.protobuf.FeatureSet.Utf8ValidationB#\x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\t\x12\x04NONE\x18\xe6\x07\xa2\x01\x0b\x12\x06VERIFY\x18\xe7\x07R\x0eutf8Validation\x12x\n\x10message_encoding\x18\x05 \x01(\x0e\x32+.google.protobuf.FeatureSet.MessageEncodingB \x88\x01\x01\x98\x01\x04\x98\x01\x01\xa2\x01\x14\x12\x0fLENGTH_PREFIXED\x18\xe6\x07R\x0fmessageEncoding\x12|\n\x0bjson_format\x18\x06 \x01(\x0e\x32&.google.protobuf.FeatureSet.JsonFormatB3\x88\x01\x01\x98\x01\x03\x98\x01\x06\x98\x01\x01\xa2\x01\x17\x12\x12LEGACY_BEST_EFFORT\x18\xe6\x07\xa2\x01\n\x12\x05\x41LLOW\x18\xe7\x07R\njsonFormat\"\\\n\rFieldPresence\x12\x1a\n\x16\x46IELD_PRESENCE_UNKNOWN\x10\x00\x12\x0c\n\x08\x45XPLICIT\x10\x01\x12\x0c\n\x08IMPLICIT\x10\x02\x12\x13\n\x0fLEGACY_REQUIRED\x10\x03\"7\n\x08\x45numType\x12\x15\n\x11\x45NUM_TYPE_UNKNOWN\x10\x00\x12\x08\n\x04OPEN\x10\x01\x12\n\n\x06\x43LOSED\x10\x02\"V\n\x15RepeatedFieldEncoding\x12#\n\x1fREPEATED_FIELD_ENCODING_UNKNOWN\x10\x00\x12\n\n\x06PACKED\x10\x01\x12\x0c\n\x08\x45XPANDED\x10\x02\"C\n\x0eUtf8Validation\x12\x1b\n\x17UTF8_VALIDATION_UNKNOWN\x10\x00\x12\x08\n\x04NONE\x10\x01\x12\n\n\x06VERIFY\x10\x02\"S\n\x0fMessageEncoding\x12\x1c\n\x18MESSAGE_ENCODING_UNKNOWN\x10\x00\x12\x13\n\x0fLENGTH_PREFIXED\x10\x01\x12\r\n\tDELIMITED\x10\x02\"H\n\nJsonFormat\x12\x17\n\x13JSON_FORMAT_UNKNOWN\x10\x00\x12\t\n\x05\x41LLOW\x10\x01\x12\x16\n\x12LEGACY_BEST_EFFORT\x10\x02*\x06\x08\xe8\x07\x10\xe9\x07*\x06\x08\xe9\x07\x10\xea\x07*\x06\x08\x8bN\x10\x90NJ\x06\x08\xe7\x07\x10\xe8\x07\"\xfe\x02\n\x12\x46\x65\x61tureSetDefaults\x12X\n\x08\x64\x65\x66\x61ults\x18\x01 \x03(\x0b\x32<.google.protobuf.FeatureSetDefaults.FeatureSetEditionDefaultR\x08\x64\x65\x66\x61ults\x12\x41\n\x0fminimum_edition\x18\x04 \x01(\x0e\x32\x18.google.protobuf.EditionR\x0eminimumEdition\x12\x41\n\x0fmaximum_edition\x18\x05 \x01(\x0e\x32\x18.google.protobuf.EditionR\x0emaximumEdition\x1a\x87\x01\n\x18\x46\x65\x61tureSetEditionDefault\x12\x32\n\x07\x65\x64ition\x18\x03 \x01(\x0e\x32\x18.google.protobuf.EditionR\x07\x65\x64ition\x12\x37\n\x08\x66\x65\x61tures\x18\x02 \x01(\x0b\x32\x1b.google.protobuf.FeatureSetR\x08\x66\x65\x61tures\"\xa7\x02\n\x0eSourceCodeInfo\x12\x44\n\x08location\x18\x01 \x03(\x0b\x32(.google.protobuf.SourceCodeInfo.LocationR\x08location\x1a\xce\x01\n\x08Location\x12\x16\n\x04path\x18\x01 \x03(\x05\x42\x02\x10\x01R\x04path\x12\x16\n\x04span\x18\x02 \x03(\x05\x42\x02\x10\x01R\x04span\x12)\n\x10leading_comments\x18\x03 \x01(\tR\x0fleadingComments\x12+\n\x11trailing_comments\x18\x04 \x01(\tR\x10trailingComments\x12:\n\x19leading_detached_comments\x18\x06 \x03(\tR\x17leadingDetachedComments\"\xd0\x02\n\x11GeneratedCodeInfo\x12M\n\nannotation\x18\x01 \x03(\x0b\x32-.google.protobuf.GeneratedCodeInfo.AnnotationR\nannotation\x1a\xeb\x01\n\nAnnotation\x12\x16\n\x04path\x18\x01 \x03(\x05\x42\x02\x10\x01R\x04path\x12\x1f\n\x0bsource_file\x18\x02 \x01(\tR\nsourceFile\x12\x14\n\x05\x62\x65gin\x18\x03 \x01(\x05R\x05\x62\x65gin\x12\x10\n\x03\x65nd\x18\x04 \x01(\x05R\x03\x65nd\x12R\n\x08semantic\x18\x05 \x01(\x0e\x32\x36.google.protobuf.GeneratedCodeInfo.Annotation.SemanticR\x08semantic\"(\n\x08Semantic\x12\x08\n\x04NONE\x10\x00\x12\x07\n\x03SET\x10\x01\x12\t\n\x05\x41LIAS\x10\x02*\xea\x01\n\x07\x45\x64ition\x12\x13\n\x0f\x45\x44ITION_UNKNOWN\x10\x00\x12\x13\n\x0e\x45\x44ITION_PROTO2\x10\xe6\x07\x12\x13\n\x0e\x45\x44ITION_PROTO3\x10\xe7\x07\x12\x11\n\x0c\x45\x44ITION_2023\x10\xe8\x07\x12\x17\n\x13\x45\x44ITION_1_TEST_ONLY\x10\x01\x12\x17\n\x13\x45\x44ITION_2_TEST_ONLY\x10\x02\x12\x1d\n\x17\x45\x44ITION_99997_TEST_ONLY\x10\x9d\x8d\x06\x12\x1d\n\x17\x45\x44ITION_99998_TEST_ONLY\x10\x9e\x8d\x06\x12\x1d\n\x17\x45\x44ITION_99999_TEST_ONLY\x10\x9f\x8d\x06\x42~\n\x13\x63om.google.protobufB\x10\x44\x65scriptorProtosH\x01Z-google.golang.org/protobuf/types/descriptorpb\xf8\x01\x01\xa2\x02\x03GPB\xaa\x02\x1aGoogle.Protobuf.Reflection')

_globals = globals()
if _descriptor._USE_C_DESCRIPTORS == False:
  _EDITION = _descriptor.EnumDescriptor(
    name='Edition',
    full_name='google.protobuf.Edition',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='EDITION_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_PROTO2', index=1, number=998,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_PROTO3', index=2, number=999,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_2023', index=3, number=1000,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_1_TEST_ONLY', index=4, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_2_TEST_ONLY', index=5, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_99997_TEST_ONLY', index=6, number=99997,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_99998_TEST_ONLY', index=7, number=99998,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EDITION_99999_TEST_ONLY', index=8, number=99999,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_EDITION)

  _EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE = _descriptor.EnumDescriptor(
    name='VerificationState',
    full_name='google.protobuf.ExtensionRangeOptions.VerificationState',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='DECLARATION', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='UNVERIFIED', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE)

  _FIELDDESCRIPTORPROTO_TYPE = _descriptor.EnumDescriptor(
    name='Type',
    full_name='google.protobuf.FieldDescriptorProto.Type',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='TYPE_DOUBLE', index=0, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_FLOAT', index=1, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_INT64', index=2, number=3,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_UINT64', index=3, number=4,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_INT32', index=4, number=5,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_FIXED64', index=5, number=6,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_FIXED32', index=6, number=7,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_BOOL', index=7, number=8,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_STRING', index=8, number=9,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_GROUP', index=9, number=10,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_MESSAGE', index=10, number=11,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_BYTES', index=11, number=12,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_UINT32', index=12, number=13,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_ENUM', index=13, number=14,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_SFIXED32', index=14, number=15,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_SFIXED64', index=15, number=16,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_SINT32', index=16, number=17,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TYPE_SINT64', index=17, number=18,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDDESCRIPTORPROTO_TYPE)

  _FIELDDESCRIPTORPROTO_LABEL = _descriptor.EnumDescriptor(
    name='Label',
    full_name='google.protobuf.FieldDescriptorProto.Label',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='LABEL_OPTIONAL', index=0, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LABEL_REPEATED', index=1, number=3,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LABEL_REQUIRED', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDDESCRIPTORPROTO_LABEL)

  _FILEOPTIONS_OPTIMIZEMODE = _descriptor.EnumDescriptor(
    name='OptimizeMode',
    full_name='google.protobuf.FileOptions.OptimizeMode',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='SPEED', index=0, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='CODE_SIZE', index=1, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LITE_RUNTIME', index=2, number=3,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FILEOPTIONS_OPTIMIZEMODE)

  _FIELDOPTIONS_CTYPE = _descriptor.EnumDescriptor(
    name='CType',
    full_name='google.protobuf.FieldOptions.CType',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='STRING', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='CORD', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='STRING_PIECE', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDOPTIONS_CTYPE)

  _FIELDOPTIONS_JSTYPE = _descriptor.EnumDescriptor(
    name='JSType',
    full_name='google.protobuf.FieldOptions.JSType',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='JS_NORMAL', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='JS_STRING', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='JS_NUMBER', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDOPTIONS_JSTYPE)

  _FIELDOPTIONS_OPTIONRETENTION = _descriptor.EnumDescriptor(
    name='OptionRetention',
    full_name='google.protobuf.FieldOptions.OptionRetention',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='RETENTION_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='RETENTION_RUNTIME', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='RETENTION_SOURCE', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDOPTIONS_OPTIONRETENTION)

  _FIELDOPTIONS_OPTIONTARGETTYPE = _descriptor.EnumDescriptor(
    name='OptionTargetType',
    full_name='google.protobuf.FieldOptions.OptionTargetType',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_FILE', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_EXTENSION_RANGE', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_MESSAGE', index=3, number=3,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_FIELD', index=4, number=4,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_ONEOF', index=5, number=5,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_ENUM', index=6, number=6,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_ENUM_ENTRY', index=7, number=7,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_SERVICE', index=8, number=8,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='TARGET_TYPE_METHOD', index=9, number=9,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FIELDOPTIONS_OPTIONTARGETTYPE)

  _METHODOPTIONS_IDEMPOTENCYLEVEL = _descriptor.EnumDescriptor(
    name='IdempotencyLevel',
    full_name='google.protobuf.MethodOptions.IdempotencyLevel',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='IDEMPOTENCY_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='NO_SIDE_EFFECTS', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='IDEMPOTENT', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_METHODOPTIONS_IDEMPOTENCYLEVEL)

  _FEATURESET_FIELDPRESENCE = _descriptor.EnumDescriptor(
    name='FieldPresence',
    full_name='google.protobuf.FeatureSet.FieldPresence',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='FIELD_PRESENCE_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EXPLICIT', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='IMPLICIT', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LEGACY_REQUIRED', index=3, number=3,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_FIELDPRESENCE)

  _FEATURESET_ENUMTYPE = _descriptor.EnumDescriptor(
    name='EnumType',
    full_name='google.protobuf.FeatureSet.EnumType',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='ENUM_TYPE_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='OPEN', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='CLOSED', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_ENUMTYPE)

  _FEATURESET_REPEATEDFIELDENCODING = _descriptor.EnumDescriptor(
    name='RepeatedFieldEncoding',
    full_name='google.protobuf.FeatureSet.RepeatedFieldEncoding',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='REPEATED_FIELD_ENCODING_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='PACKED', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='EXPANDED', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_REPEATEDFIELDENCODING)

  _FEATURESET_UTF8VALIDATION = _descriptor.EnumDescriptor(
    name='Utf8Validation',
    full_name='google.protobuf.FeatureSet.Utf8Validation',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='UTF8_VALIDATION_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='NONE', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='VERIFY', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_UTF8VALIDATION)

  _FEATURESET_MESSAGEENCODING = _descriptor.EnumDescriptor(
    name='MessageEncoding',
    full_name='google.protobuf.FeatureSet.MessageEncoding',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='MESSAGE_ENCODING_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LENGTH_PREFIXED', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='DELIMITED', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_MESSAGEENCODING)

  _FEATURESET_JSONFORMAT = _descriptor.EnumDescriptor(
    name='JsonFormat',
    full_name='google.protobuf.FeatureSet.JsonFormat',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='JSON_FORMAT_UNKNOWN', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='ALLOW', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='LEGACY_BEST_EFFORT', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_FEATURESET_JSONFORMAT)

  _GENERATEDCODEINFO_ANNOTATION_SEMANTIC = _descriptor.EnumDescriptor(
    name='Semantic',
    full_name='google.protobuf.GeneratedCodeInfo.Annotation.Semantic',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
      _descriptor.EnumValueDescriptor(
        name='NONE', index=0, number=0,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='SET', index=1, number=1,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
      _descriptor.EnumValueDescriptor(
        name='ALIAS', index=2, number=2,
        serialized_options=None,
        type=None,
        create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
  )
  _sym_db.RegisterEnumDescriptor(_GENERATEDCODEINFO_ANNOTATION_SEMANTIC)


  _FILEDESCRIPTORSET = _descriptor.Descriptor(
    name='FileDescriptorSet',
    full_name='google.protobuf.FileDescriptorSet',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='file', full_name='google.protobuf.FileDescriptorSet.file', index=0,
        number=1, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='file', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _FILEDESCRIPTORPROTO = _descriptor.Descriptor(
    name='FileDescriptorProto',
    full_name='google.protobuf.FileDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.FileDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='package', full_name='google.protobuf.FileDescriptorProto.package', index=1,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='package', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='dependency', full_name='google.protobuf.FileDescriptorProto.dependency', index=2,
        number=3, type=9, cpp_type=9, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='dependency', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='public_dependency', full_name='google.protobuf.FileDescriptorProto.public_dependency', index=3,
        number=10, type=5, cpp_type=1, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='publicDependency', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='weak_dependency', full_name='google.protobuf.FileDescriptorProto.weak_dependency', index=4,
        number=11, type=5, cpp_type=1, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='weakDependency', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='message_type', full_name='google.protobuf.FileDescriptorProto.message_type', index=5,
        number=4, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='messageType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='enum_type', full_name='google.protobuf.FileDescriptorProto.enum_type', index=6,
        number=5, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='enumType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='service', full_name='google.protobuf.FileDescriptorProto.service', index=7,
        number=6, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='service', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='extension', full_name='google.protobuf.FileDescriptorProto.extension', index=8,
        number=7, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='extension', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.FileDescriptorProto.options', index=9,
        number=8, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='source_code_info', full_name='google.protobuf.FileDescriptorProto.source_code_info', index=10,
        number=9, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='sourceCodeInfo', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='syntax', full_name='google.protobuf.FileDescriptorProto.syntax', index=11,
        number=12, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='syntax', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='edition', full_name='google.protobuf.FileDescriptorProto.edition', index=12,
        number=14, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='edition', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _DESCRIPTORPROTO_EXTENSIONRANGE = _descriptor.Descriptor(
    name='ExtensionRange',
    full_name='google.protobuf.DescriptorProto.ExtensionRange',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='start', full_name='google.protobuf.DescriptorProto.ExtensionRange.start', index=0,
        number=1, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='start', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='end', full_name='google.protobuf.DescriptorProto.ExtensionRange.end', index=1,
        number=2, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='end', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.DescriptorProto.ExtensionRange.options', index=2,
        number=3, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _DESCRIPTORPROTO_RESERVEDRANGE = _descriptor.Descriptor(
    name='ReservedRange',
    full_name='google.protobuf.DescriptorProto.ReservedRange',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='start', full_name='google.protobuf.DescriptorProto.ReservedRange.start', index=0,
        number=1, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='start', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='end', full_name='google.protobuf.DescriptorProto.ReservedRange.end', index=1,
        number=2, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='end', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _DESCRIPTORPROTO = _descriptor.Descriptor(
    name='DescriptorProto',
    full_name='google.protobuf.DescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.DescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='field', full_name='google.protobuf.DescriptorProto.field', index=1,
        number=2, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='field', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='extension', full_name='google.protobuf.DescriptorProto.extension', index=2,
        number=6, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='extension', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='nested_type', full_name='google.protobuf.DescriptorProto.nested_type', index=3,
        number=3, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='nestedType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='enum_type', full_name='google.protobuf.DescriptorProto.enum_type', index=4,
        number=4, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='enumType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='extension_range', full_name='google.protobuf.DescriptorProto.extension_range', index=5,
        number=5, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='extensionRange', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='oneof_decl', full_name='google.protobuf.DescriptorProto.oneof_decl', index=6,
        number=8, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='oneofDecl', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.DescriptorProto.options', index=7,
        number=7, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='reserved_range', full_name='google.protobuf.DescriptorProto.reserved_range', index=8,
        number=9, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='reservedRange', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='reserved_name', full_name='google.protobuf.DescriptorProto.reserved_name', index=9,
        number=10, type=9, cpp_type=9, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='reservedName', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_DESCRIPTORPROTO_EXTENSIONRANGE, _DESCRIPTORPROTO_RESERVEDRANGE, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _EXTENSIONRANGEOPTIONS_DECLARATION = _descriptor.Descriptor(
    name='Declaration',
    full_name='google.protobuf.ExtensionRangeOptions.Declaration',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='number', full_name='google.protobuf.ExtensionRangeOptions.Declaration.number', index=0,
        number=1, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='number', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='full_name', full_name='google.protobuf.ExtensionRangeOptions.Declaration.full_name', index=1,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='fullName', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='type', full_name='google.protobuf.ExtensionRangeOptions.Declaration.type', index=2,
        number=3, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='type', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='reserved', full_name='google.protobuf.ExtensionRangeOptions.Declaration.reserved', index=3,
        number=5, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='reserved', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='repeated', full_name='google.protobuf.ExtensionRangeOptions.Declaration.repeated', index=4,
        number=6, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='repeated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _EXTENSIONRANGEOPTIONS = _descriptor.Descriptor(
    name='ExtensionRangeOptions',
    full_name='google.protobuf.ExtensionRangeOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.ExtensionRangeOptions.uninterpreted_option', index=0,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='declaration', full_name='google.protobuf.ExtensionRangeOptions.declaration', index=1,
        number=2, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\002', json_name='declaration', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.ExtensionRangeOptions.features', index=2,
        number=50, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='verification', full_name='google.protobuf.ExtensionRangeOptions.verification', index=3,
        number=3, type=14, cpp_type=8, label=1,
        has_default_value=True, default_value=1,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='verification', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_EXTENSIONRANGEOPTIONS_DECLARATION, ],
    enum_types=[
      _EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE,
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _FIELDDESCRIPTORPROTO = _descriptor.Descriptor(
    name='FieldDescriptorProto',
    full_name='google.protobuf.FieldDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.FieldDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='number', full_name='google.protobuf.FieldDescriptorProto.number', index=1,
        number=3, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='number', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='label', full_name='google.protobuf.FieldDescriptorProto.label', index=2,
        number=4, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=1,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='label', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='type', full_name='google.protobuf.FieldDescriptorProto.type', index=3,
        number=5, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=1,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='type', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='type_name', full_name='google.protobuf.FieldDescriptorProto.type_name', index=4,
        number=6, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='typeName', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='extendee', full_name='google.protobuf.FieldDescriptorProto.extendee', index=5,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='extendee', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='default_value', full_name='google.protobuf.FieldDescriptorProto.default_value', index=6,
        number=7, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='defaultValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='oneof_index', full_name='google.protobuf.FieldDescriptorProto.oneof_index', index=7,
        number=9, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='oneofIndex', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='json_name', full_name='google.protobuf.FieldDescriptorProto.json_name', index=8,
        number=10, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='jsonName', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.FieldDescriptorProto.options', index=9,
        number=8, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='proto3_optional', full_name='google.protobuf.FieldDescriptorProto.proto3_optional', index=10,
        number=17, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='proto3Optional', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
      _FIELDDESCRIPTORPROTO_TYPE,
      _FIELDDESCRIPTORPROTO_LABEL,
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _ONEOFDESCRIPTORPROTO = _descriptor.Descriptor(
    name='OneofDescriptorProto',
    full_name='google.protobuf.OneofDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.OneofDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.OneofDescriptorProto.options', index=1,
        number=2, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE = _descriptor.Descriptor(
    name='EnumReservedRange',
    full_name='google.protobuf.EnumDescriptorProto.EnumReservedRange',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='start', full_name='google.protobuf.EnumDescriptorProto.EnumReservedRange.start', index=0,
        number=1, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='start', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='end', full_name='google.protobuf.EnumDescriptorProto.EnumReservedRange.end', index=1,
        number=2, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='end', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _ENUMDESCRIPTORPROTO = _descriptor.Descriptor(
    name='EnumDescriptorProto',
    full_name='google.protobuf.EnumDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.EnumDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='value', full_name='google.protobuf.EnumDescriptorProto.value', index=1,
        number=2, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='value', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.EnumDescriptorProto.options', index=2,
        number=3, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='reserved_range', full_name='google.protobuf.EnumDescriptorProto.reserved_range', index=3,
        number=4, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='reservedRange', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='reserved_name', full_name='google.protobuf.EnumDescriptorProto.reserved_name', index=4,
        number=5, type=9, cpp_type=9, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='reservedName', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _ENUMVALUEDESCRIPTORPROTO = _descriptor.Descriptor(
    name='EnumValueDescriptorProto',
    full_name='google.protobuf.EnumValueDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.EnumValueDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='number', full_name='google.protobuf.EnumValueDescriptorProto.number', index=1,
        number=2, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='number', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.EnumValueDescriptorProto.options', index=2,
        number=3, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _SERVICEDESCRIPTORPROTO = _descriptor.Descriptor(
    name='ServiceDescriptorProto',
    full_name='google.protobuf.ServiceDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.ServiceDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='method', full_name='google.protobuf.ServiceDescriptorProto.method', index=1,
        number=2, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='method', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.ServiceDescriptorProto.options', index=2,
        number=3, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _METHODDESCRIPTORPROTO = _descriptor.Descriptor(
    name='MethodDescriptorProto',
    full_name='google.protobuf.MethodDescriptorProto',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.MethodDescriptorProto.name', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='input_type', full_name='google.protobuf.MethodDescriptorProto.input_type', index=1,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='inputType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='output_type', full_name='google.protobuf.MethodDescriptorProto.output_type', index=2,
        number=3, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='outputType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='options', full_name='google.protobuf.MethodDescriptorProto.options', index=3,
        number=4, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='options', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='client_streaming', full_name='google.protobuf.MethodDescriptorProto.client_streaming', index=4,
        number=5, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='clientStreaming', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='server_streaming', full_name='google.protobuf.MethodDescriptorProto.server_streaming', index=5,
        number=6, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='serverStreaming', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _FILEOPTIONS = _descriptor.Descriptor(
    name='FileOptions',
    full_name='google.protobuf.FileOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='java_package', full_name='google.protobuf.FileOptions.java_package', index=0,
        number=1, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='javaPackage', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='java_outer_classname', full_name='google.protobuf.FileOptions.java_outer_classname', index=1,
        number=8, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='javaOuterClassname', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='java_multiple_files', full_name='google.protobuf.FileOptions.java_multiple_files', index=2,
        number=10, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='javaMultipleFiles', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='java_generate_equals_and_hash', full_name='google.protobuf.FileOptions.java_generate_equals_and_hash', index=3,
        number=20, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\030\001', json_name='javaGenerateEqualsAndHash', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='java_string_check_utf8', full_name='google.protobuf.FileOptions.java_string_check_utf8', index=4,
        number=27, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='javaStringCheckUtf8', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='optimize_for', full_name='google.protobuf.FileOptions.optimize_for', index=5,
        number=9, type=14, cpp_type=8, label=1,
        has_default_value=True, default_value=1,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='optimizeFor', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='go_package', full_name='google.protobuf.FileOptions.go_package', index=6,
        number=11, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='goPackage', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='cc_generic_services', full_name='google.protobuf.FileOptions.cc_generic_services', index=7,
        number=16, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='ccGenericServices', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='java_generic_services', full_name='google.protobuf.FileOptions.java_generic_services', index=8,
        number=17, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='javaGenericServices', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='py_generic_services', full_name='google.protobuf.FileOptions.py_generic_services', index=9,
        number=18, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='pyGenericServices', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='php_generic_services', full_name='google.protobuf.FileOptions.php_generic_services', index=10,
        number=42, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='phpGenericServices', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.FileOptions.deprecated', index=11,
        number=23, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='cc_enable_arenas', full_name='google.protobuf.FileOptions.cc_enable_arenas', index=12,
        number=31, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=True,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='ccEnableArenas', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='objc_class_prefix', full_name='google.protobuf.FileOptions.objc_class_prefix', index=13,
        number=36, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='objcClassPrefix', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='csharp_namespace', full_name='google.protobuf.FileOptions.csharp_namespace', index=14,
        number=37, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='csharpNamespace', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='swift_prefix', full_name='google.protobuf.FileOptions.swift_prefix', index=15,
        number=39, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='swiftPrefix', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='php_class_prefix', full_name='google.protobuf.FileOptions.php_class_prefix', index=16,
        number=40, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='phpClassPrefix', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='php_namespace', full_name='google.protobuf.FileOptions.php_namespace', index=17,
        number=41, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='phpNamespace', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='php_metadata_namespace', full_name='google.protobuf.FileOptions.php_metadata_namespace', index=18,
        number=44, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='phpMetadataNamespace', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='ruby_package', full_name='google.protobuf.FileOptions.ruby_package', index=19,
        number=45, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='rubyPackage', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.FileOptions.features', index=20,
        number=50, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.FileOptions.uninterpreted_option', index=21,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
      _FILEOPTIONS_OPTIMIZEMODE,
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _MESSAGEOPTIONS = _descriptor.Descriptor(
    name='MessageOptions',
    full_name='google.protobuf.MessageOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='message_set_wire_format', full_name='google.protobuf.MessageOptions.message_set_wire_format', index=0,
        number=1, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='messageSetWireFormat', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='no_standard_descriptor_accessor', full_name='google.protobuf.MessageOptions.no_standard_descriptor_accessor', index=1,
        number=2, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='noStandardDescriptorAccessor', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.MessageOptions.deprecated', index=2,
        number=3, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='map_entry', full_name='google.protobuf.MessageOptions.map_entry', index=3,
        number=7, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='mapEntry', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated_legacy_json_field_conflicts', full_name='google.protobuf.MessageOptions.deprecated_legacy_json_field_conflicts', index=4,
        number=11, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\030\001', json_name='deprecatedLegacyJsonFieldConflicts', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.MessageOptions.features', index=5,
        number=12, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.MessageOptions.uninterpreted_option', index=6,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _FIELDOPTIONS_EDITIONDEFAULT = _descriptor.Descriptor(
    name='EditionDefault',
    full_name='google.protobuf.FieldOptions.EditionDefault',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='edition', full_name='google.protobuf.FieldOptions.EditionDefault.edition', index=0,
        number=3, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='edition', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='value', full_name='google.protobuf.FieldOptions.EditionDefault.value', index=1,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='value', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _FIELDOPTIONS = _descriptor.Descriptor(
    name='FieldOptions',
    full_name='google.protobuf.FieldOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='ctype', full_name='google.protobuf.FieldOptions.ctype', index=0,
        number=1, type=14, cpp_type=8, label=1,
        has_default_value=True, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='ctype', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='packed', full_name='google.protobuf.FieldOptions.packed', index=1,
        number=2, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='packed', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='jstype', full_name='google.protobuf.FieldOptions.jstype', index=2,
        number=6, type=14, cpp_type=8, label=1,
        has_default_value=True, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='jstype', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='lazy', full_name='google.protobuf.FieldOptions.lazy', index=3,
        number=5, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='lazy', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='unverified_lazy', full_name='google.protobuf.FieldOptions.unverified_lazy', index=4,
        number=15, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='unverifiedLazy', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.FieldOptions.deprecated', index=5,
        number=3, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='weak', full_name='google.protobuf.FieldOptions.weak', index=6,
        number=10, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='weak', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='debug_redact', full_name='google.protobuf.FieldOptions.debug_redact', index=7,
        number=16, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='debugRedact', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='retention', full_name='google.protobuf.FieldOptions.retention', index=8,
        number=17, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='retention', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='targets', full_name='google.protobuf.FieldOptions.targets', index=9,
        number=19, type=14, cpp_type=8, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='targets', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='edition_defaults', full_name='google.protobuf.FieldOptions.edition_defaults', index=10,
        number=20, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='editionDefaults', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.FieldOptions.features', index=11,
        number=21, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.FieldOptions.uninterpreted_option', index=12,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_FIELDOPTIONS_EDITIONDEFAULT, ],
    enum_types=[
      _FIELDOPTIONS_CTYPE,
      _FIELDOPTIONS_JSTYPE,
      _FIELDOPTIONS_OPTIONRETENTION,
      _FIELDOPTIONS_OPTIONTARGETTYPE,
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _ONEOFOPTIONS = _descriptor.Descriptor(
    name='OneofOptions',
    full_name='google.protobuf.OneofOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.OneofOptions.features', index=0,
        number=1, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.OneofOptions.uninterpreted_option', index=1,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _ENUMOPTIONS = _descriptor.Descriptor(
    name='EnumOptions',
    full_name='google.protobuf.EnumOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='allow_alias', full_name='google.protobuf.EnumOptions.allow_alias', index=0,
        number=2, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='allowAlias', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.EnumOptions.deprecated', index=1,
        number=3, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated_legacy_json_field_conflicts', full_name='google.protobuf.EnumOptions.deprecated_legacy_json_field_conflicts', index=2,
        number=6, type=8, cpp_type=7, label=1,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\030\001', json_name='deprecatedLegacyJsonFieldConflicts', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.EnumOptions.features', index=3,
        number=7, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.EnumOptions.uninterpreted_option', index=4,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _ENUMVALUEOPTIONS = _descriptor.Descriptor(
    name='EnumValueOptions',
    full_name='google.protobuf.EnumValueOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.EnumValueOptions.deprecated', index=0,
        number=1, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.EnumValueOptions.features', index=1,
        number=2, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='debug_redact', full_name='google.protobuf.EnumValueOptions.debug_redact', index=2,
        number=3, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='debugRedact', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.EnumValueOptions.uninterpreted_option', index=3,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _SERVICEOPTIONS = _descriptor.Descriptor(
    name='ServiceOptions',
    full_name='google.protobuf.ServiceOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.ServiceOptions.features', index=0,
        number=34, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.ServiceOptions.deprecated', index=1,
        number=33, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.ServiceOptions.uninterpreted_option', index=2,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _METHODOPTIONS = _descriptor.Descriptor(
    name='MethodOptions',
    full_name='google.protobuf.MethodOptions',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='deprecated', full_name='google.protobuf.MethodOptions.deprecated', index=0,
        number=33, type=8, cpp_type=7, label=1,
        has_default_value=True, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='deprecated', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='idempotency_level', full_name='google.protobuf.MethodOptions.idempotency_level', index=1,
        number=34, type=14, cpp_type=8, label=1,
        has_default_value=True, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='idempotencyLevel', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.MethodOptions.features', index=2,
        number=35, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='uninterpreted_option', full_name='google.protobuf.MethodOptions.uninterpreted_option', index=3,
        number=999, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='uninterpretedOption', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
      _METHODOPTIONS_IDEMPOTENCYLEVEL,
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 536870912), ],
    oneofs=[
    ],
  )


  _UNINTERPRETEDOPTION_NAMEPART = _descriptor.Descriptor(
    name='NamePart',
    full_name='google.protobuf.UninterpretedOption.NamePart',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name_part', full_name='google.protobuf.UninterpretedOption.NamePart.name_part', index=0,
        number=1, type=9, cpp_type=9, label=2,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='namePart', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='is_extension', full_name='google.protobuf.UninterpretedOption.NamePart.is_extension', index=1,
        number=2, type=8, cpp_type=7, label=2,
        has_default_value=False, default_value=False,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='isExtension', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _UNINTERPRETEDOPTION = _descriptor.Descriptor(
    name='UninterpretedOption',
    full_name='google.protobuf.UninterpretedOption',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='name', full_name='google.protobuf.UninterpretedOption.name', index=0,
        number=2, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='name', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='identifier_value', full_name='google.protobuf.UninterpretedOption.identifier_value', index=1,
        number=3, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='identifierValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='positive_int_value', full_name='google.protobuf.UninterpretedOption.positive_int_value', index=2,
        number=4, type=4, cpp_type=4, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='positiveIntValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='negative_int_value', full_name='google.protobuf.UninterpretedOption.negative_int_value', index=3,
        number=5, type=3, cpp_type=2, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='negativeIntValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='double_value', full_name='google.protobuf.UninterpretedOption.double_value', index=4,
        number=6, type=1, cpp_type=5, label=1,
        has_default_value=False, default_value=float(0),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='doubleValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='string_value', full_name='google.protobuf.UninterpretedOption.string_value', index=5,
        number=7, type=12, cpp_type=9, label=1,
        has_default_value=False, default_value=b"",
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='stringValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='aggregate_value', full_name='google.protobuf.UninterpretedOption.aggregate_value', index=6,
        number=8, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='aggregateValue', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_UNINTERPRETEDOPTION_NAMEPART, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _FEATURESET = _descriptor.Descriptor(
    name='FeatureSet',
    full_name='google.protobuf.FeatureSet',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='field_presence', full_name='google.protobuf.FeatureSet.field_presence', index=0,
        number=1, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\004\230\001\001\242\001\r\022\010EXPLICIT\030\346\007\242\001\r\022\010IMPLICIT\030\347\007\242\001\r\022\010EXPLICIT\030\350\007', json_name='fieldPresence', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='enum_type', full_name='google.protobuf.FeatureSet.enum_type', index=1,
        number=2, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\006\230\001\001\242\001\013\022\006CLOSED\030\346\007\242\001\t\022\004OPEN\030\347\007', json_name='enumType', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='repeated_field_encoding', full_name='google.protobuf.FeatureSet.repeated_field_encoding', index=2,
        number=3, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\004\230\001\001\242\001\r\022\010EXPANDED\030\346\007\242\001\013\022\006PACKED\030\347\007', json_name='repeatedFieldEncoding', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='utf8_validation', full_name='google.protobuf.FeatureSet.utf8_validation', index=3,
        number=4, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\004\230\001\001\242\001\t\022\004NONE\030\346\007\242\001\013\022\006VERIFY\030\347\007', json_name='utf8Validation', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='message_encoding', full_name='google.protobuf.FeatureSet.message_encoding', index=4,
        number=5, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\004\230\001\001\242\001\024\022\017LENGTH_PREFIXED\030\346\007', json_name='messageEncoding', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='json_format', full_name='google.protobuf.FeatureSet.json_format', index=5,
        number=6, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\210\001\001\230\001\003\230\001\006\230\001\001\242\001\027\022\022LEGACY_BEST_EFFORT\030\346\007\242\001\n\022\005ALLOW\030\347\007', json_name='jsonFormat', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
      _FEATURESET_FIELDPRESENCE,
      _FEATURESET_ENUMTYPE,
      _FEATURESET_REPEATEDFIELDENCODING,
      _FEATURESET_UTF8VALIDATION,
      _FEATURESET_MESSAGEENCODING,
      _FEATURESET_JSONFORMAT,
    ],
    serialized_options=None,
    is_extendable=True,
    syntax='proto2',
    extension_ranges=[(1000, 1001), (1001, 1002), (9995, 10000), ],
    oneofs=[
    ],
  )


  _FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT = _descriptor.Descriptor(
    name='FeatureSetEditionDefault',
    full_name='google.protobuf.FeatureSetDefaults.FeatureSetEditionDefault',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='edition', full_name='google.protobuf.FeatureSetDefaults.FeatureSetEditionDefault.edition', index=0,
        number=3, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='edition', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='features', full_name='google.protobuf.FeatureSetDefaults.FeatureSetEditionDefault.features', index=1,
        number=2, type=11, cpp_type=10, label=1,
        has_default_value=False, default_value=None,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='features', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _FEATURESETDEFAULTS = _descriptor.Descriptor(
    name='FeatureSetDefaults',
    full_name='google.protobuf.FeatureSetDefaults',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='defaults', full_name='google.protobuf.FeatureSetDefaults.defaults', index=0,
        number=1, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='defaults', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='minimum_edition', full_name='google.protobuf.FeatureSetDefaults.minimum_edition', index=1,
        number=4, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='minimumEdition', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='maximum_edition', full_name='google.protobuf.FeatureSetDefaults.maximum_edition', index=2,
        number=5, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='maximumEdition', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _SOURCECODEINFO_LOCATION = _descriptor.Descriptor(
    name='Location',
    full_name='google.protobuf.SourceCodeInfo.Location',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='path', full_name='google.protobuf.SourceCodeInfo.Location.path', index=0,
        number=1, type=5, cpp_type=1, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\020\001', json_name='path', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='span', full_name='google.protobuf.SourceCodeInfo.Location.span', index=1,
        number=2, type=5, cpp_type=1, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\020\001', json_name='span', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='leading_comments', full_name='google.protobuf.SourceCodeInfo.Location.leading_comments', index=2,
        number=3, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='leadingComments', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='trailing_comments', full_name='google.protobuf.SourceCodeInfo.Location.trailing_comments', index=3,
        number=4, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='trailingComments', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='leading_detached_comments', full_name='google.protobuf.SourceCodeInfo.Location.leading_detached_comments', index=4,
        number=6, type=9, cpp_type=9, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='leadingDetachedComments', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _SOURCECODEINFO = _descriptor.Descriptor(
    name='SourceCodeInfo',
    full_name='google.protobuf.SourceCodeInfo',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='location', full_name='google.protobuf.SourceCodeInfo.location', index=0,
        number=1, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='location', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_SOURCECODEINFO_LOCATION, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )


  _GENERATEDCODEINFO_ANNOTATION = _descriptor.Descriptor(
    name='Annotation',
    full_name='google.protobuf.GeneratedCodeInfo.Annotation',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='path', full_name='google.protobuf.GeneratedCodeInfo.Annotation.path', index=0,
        number=1, type=5, cpp_type=1, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=b'\020\001', json_name='path', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='source_file', full_name='google.protobuf.GeneratedCodeInfo.Annotation.source_file', index=1,
        number=2, type=9, cpp_type=9, label=1,
        has_default_value=False, default_value=b"".decode('utf-8'),
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='sourceFile', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='begin', full_name='google.protobuf.GeneratedCodeInfo.Annotation.begin', index=2,
        number=3, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='begin', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='end', full_name='google.protobuf.GeneratedCodeInfo.Annotation.end', index=3,
        number=4, type=5, cpp_type=1, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='end', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
      _descriptor.FieldDescriptor(
        name='semantic', full_name='google.protobuf.GeneratedCodeInfo.Annotation.semantic', index=4,
        number=5, type=14, cpp_type=8, label=1,
        has_default_value=False, default_value=0,
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='semantic', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[],
    enum_types=[
      _GENERATEDCODEINFO_ANNOTATION_SEMANTIC,
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _GENERATEDCODEINFO = _descriptor.Descriptor(
    name='GeneratedCodeInfo',
    full_name='google.protobuf.GeneratedCodeInfo',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='annotation', full_name='google.protobuf.GeneratedCodeInfo.annotation', index=0,
        number=1, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, json_name='annotation', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    ],
    extensions=[
    ],
    nested_types=[_GENERATEDCODEINFO_ANNOTATION, ],
    enum_types=[
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto2',
    extension_ranges=[],
    oneofs=[
    ],
  )

  _FILEDESCRIPTORSET.fields_by_name['file'].message_type = _FILEDESCRIPTORPROTO
  _FILEDESCRIPTORPROTO.fields_by_name['message_type'].message_type = _DESCRIPTORPROTO
  _FILEDESCRIPTORPROTO.fields_by_name['enum_type'].message_type = _ENUMDESCRIPTORPROTO
  _FILEDESCRIPTORPROTO.fields_by_name['service'].message_type = _SERVICEDESCRIPTORPROTO
  _FILEDESCRIPTORPROTO.fields_by_name['extension'].message_type = _FIELDDESCRIPTORPROTO
  _FILEDESCRIPTORPROTO.fields_by_name['options'].message_type = _FILEOPTIONS
  _FILEDESCRIPTORPROTO.fields_by_name['source_code_info'].message_type = _SOURCECODEINFO
  _FILEDESCRIPTORPROTO.fields_by_name['edition'].enum_type = _EDITION
  _DESCRIPTORPROTO_EXTENSIONRANGE.fields_by_name['options'].message_type = _EXTENSIONRANGEOPTIONS
  _DESCRIPTORPROTO_EXTENSIONRANGE.containing_type = _DESCRIPTORPROTO
  _DESCRIPTORPROTO_RESERVEDRANGE.containing_type = _DESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['field'].message_type = _FIELDDESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['extension'].message_type = _FIELDDESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['nested_type'].message_type = _DESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['enum_type'].message_type = _ENUMDESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['extension_range'].message_type = _DESCRIPTORPROTO_EXTENSIONRANGE
  _DESCRIPTORPROTO.fields_by_name['oneof_decl'].message_type = _ONEOFDESCRIPTORPROTO
  _DESCRIPTORPROTO.fields_by_name['options'].message_type = _MESSAGEOPTIONS
  _DESCRIPTORPROTO.fields_by_name['reserved_range'].message_type = _DESCRIPTORPROTO_RESERVEDRANGE
  _EXTENSIONRANGEOPTIONS_DECLARATION.containing_type = _EXTENSIONRANGEOPTIONS
  _EXTENSIONRANGEOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _EXTENSIONRANGEOPTIONS.fields_by_name['declaration'].message_type = _EXTENSIONRANGEOPTIONS_DECLARATION
  _EXTENSIONRANGEOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _EXTENSIONRANGEOPTIONS.fields_by_name['verification'].enum_type = _EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE
  _EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE.containing_type = _EXTENSIONRANGEOPTIONS
  _FIELDDESCRIPTORPROTO.fields_by_name['label'].enum_type = _FIELDDESCRIPTORPROTO_LABEL
  _FIELDDESCRIPTORPROTO.fields_by_name['type'].enum_type = _FIELDDESCRIPTORPROTO_TYPE
  _FIELDDESCRIPTORPROTO.fields_by_name['options'].message_type = _FIELDOPTIONS
  _FIELDDESCRIPTORPROTO_TYPE.containing_type = _FIELDDESCRIPTORPROTO
  _FIELDDESCRIPTORPROTO_LABEL.containing_type = _FIELDDESCRIPTORPROTO
  _ONEOFDESCRIPTORPROTO.fields_by_name['options'].message_type = _ONEOFOPTIONS
  _ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE.containing_type = _ENUMDESCRIPTORPROTO
  _ENUMDESCRIPTORPROTO.fields_by_name['value'].message_type = _ENUMVALUEDESCRIPTORPROTO
  _ENUMDESCRIPTORPROTO.fields_by_name['options'].message_type = _ENUMOPTIONS
  _ENUMDESCRIPTORPROTO.fields_by_name['reserved_range'].message_type = _ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE
  _ENUMVALUEDESCRIPTORPROTO.fields_by_name['options'].message_type = _ENUMVALUEOPTIONS
  _SERVICEDESCRIPTORPROTO.fields_by_name['method'].message_type = _METHODDESCRIPTORPROTO
  _SERVICEDESCRIPTORPROTO.fields_by_name['options'].message_type = _SERVICEOPTIONS
  _METHODDESCRIPTORPROTO.fields_by_name['options'].message_type = _METHODOPTIONS
  _FILEOPTIONS.fields_by_name['optimize_for'].enum_type = _FILEOPTIONS_OPTIMIZEMODE
  _FILEOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _FILEOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _FILEOPTIONS_OPTIMIZEMODE.containing_type = _FILEOPTIONS
  _MESSAGEOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _MESSAGEOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _FIELDOPTIONS_EDITIONDEFAULT.fields_by_name['edition'].enum_type = _EDITION
  _FIELDOPTIONS_EDITIONDEFAULT.containing_type = _FIELDOPTIONS
  _FIELDOPTIONS.fields_by_name['ctype'].enum_type = _FIELDOPTIONS_CTYPE
  _FIELDOPTIONS.fields_by_name['jstype'].enum_type = _FIELDOPTIONS_JSTYPE
  _FIELDOPTIONS.fields_by_name['retention'].enum_type = _FIELDOPTIONS_OPTIONRETENTION
  _FIELDOPTIONS.fields_by_name['targets'].enum_type = _FIELDOPTIONS_OPTIONTARGETTYPE
  _FIELDOPTIONS.fields_by_name['edition_defaults'].message_type = _FIELDOPTIONS_EDITIONDEFAULT
  _FIELDOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _FIELDOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _FIELDOPTIONS_CTYPE.containing_type = _FIELDOPTIONS
  _FIELDOPTIONS_JSTYPE.containing_type = _FIELDOPTIONS
  _FIELDOPTIONS_OPTIONRETENTION.containing_type = _FIELDOPTIONS
  _FIELDOPTIONS_OPTIONTARGETTYPE.containing_type = _FIELDOPTIONS
  _ONEOFOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _ONEOFOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _ENUMOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _ENUMOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _ENUMVALUEOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _ENUMVALUEOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _SERVICEOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _SERVICEOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _METHODOPTIONS.fields_by_name['idempotency_level'].enum_type = _METHODOPTIONS_IDEMPOTENCYLEVEL
  _METHODOPTIONS.fields_by_name['features'].message_type = _FEATURESET
  _METHODOPTIONS.fields_by_name['uninterpreted_option'].message_type = _UNINTERPRETEDOPTION
  _METHODOPTIONS_IDEMPOTENCYLEVEL.containing_type = _METHODOPTIONS
  _UNINTERPRETEDOPTION_NAMEPART.containing_type = _UNINTERPRETEDOPTION
  _UNINTERPRETEDOPTION.fields_by_name['name'].message_type = _UNINTERPRETEDOPTION_NAMEPART
  _FEATURESET.fields_by_name['field_presence'].enum_type = _FEATURESET_FIELDPRESENCE
  _FEATURESET.fields_by_name['enum_type'].enum_type = _FEATURESET_ENUMTYPE
  _FEATURESET.fields_by_name['repeated_field_encoding'].enum_type = _FEATURESET_REPEATEDFIELDENCODING
  _FEATURESET.fields_by_name['utf8_validation'].enum_type = _FEATURESET_UTF8VALIDATION
  _FEATURESET.fields_by_name['message_encoding'].enum_type = _FEATURESET_MESSAGEENCODING
  _FEATURESET.fields_by_name['json_format'].enum_type = _FEATURESET_JSONFORMAT
  _FEATURESET_FIELDPRESENCE.containing_type = _FEATURESET
  _FEATURESET_ENUMTYPE.containing_type = _FEATURESET
  _FEATURESET_REPEATEDFIELDENCODING.containing_type = _FEATURESET
  _FEATURESET_UTF8VALIDATION.containing_type = _FEATURESET
  _FEATURESET_MESSAGEENCODING.containing_type = _FEATURESET
  _FEATURESET_JSONFORMAT.containing_type = _FEATURESET
  _FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT.fields_by_name['edition'].enum_type = _EDITION
  _FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT.fields_by_name['features'].message_type = _FEATURESET
  _FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT.containing_type = _FEATURESETDEFAULTS
  _FEATURESETDEFAULTS.fields_by_name['defaults'].message_type = _FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT
  _FEATURESETDEFAULTS.fields_by_name['minimum_edition'].enum_type = _EDITION
  _FEATURESETDEFAULTS.fields_by_name['maximum_edition'].enum_type = _EDITION
  _SOURCECODEINFO_LOCATION.containing_type = _SOURCECODEINFO
  _SOURCECODEINFO.fields_by_name['location'].message_type = _SOURCECODEINFO_LOCATION
  _GENERATEDCODEINFO_ANNOTATION.fields_by_name['semantic'].enum_type = _GENERATEDCODEINFO_ANNOTATION_SEMANTIC
  _GENERATEDCODEINFO_ANNOTATION.containing_type = _GENERATEDCODEINFO
  _GENERATEDCODEINFO_ANNOTATION_SEMANTIC.containing_type = _GENERATEDCODEINFO_ANNOTATION
  _GENERATEDCODEINFO.fields_by_name['annotation'].message_type = _GENERATEDCODEINFO_ANNOTATION
  DESCRIPTOR.message_types_by_name['FileDescriptorSet'] = _FILEDESCRIPTORSET
  DESCRIPTOR.message_types_by_name['FileDescriptorProto'] = _FILEDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['DescriptorProto'] = _DESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['ExtensionRangeOptions'] = _EXTENSIONRANGEOPTIONS
  DESCRIPTOR.message_types_by_name['FieldDescriptorProto'] = _FIELDDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['OneofDescriptorProto'] = _ONEOFDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['EnumDescriptorProto'] = _ENUMDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['EnumValueDescriptorProto'] = _ENUMVALUEDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['ServiceDescriptorProto'] = _SERVICEDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['MethodDescriptorProto'] = _METHODDESCRIPTORPROTO
  DESCRIPTOR.message_types_by_name['FileOptions'] = _FILEOPTIONS
  DESCRIPTOR.message_types_by_name['MessageOptions'] = _MESSAGEOPTIONS
  DESCRIPTOR.message_types_by_name['FieldOptions'] = _FIELDOPTIONS
  DESCRIPTOR.message_types_by_name['OneofOptions'] = _ONEOFOPTIONS
  DESCRIPTOR.message_types_by_name['EnumOptions'] = _ENUMOPTIONS
  DESCRIPTOR.message_types_by_name['EnumValueOptions'] = _ENUMVALUEOPTIONS
  DESCRIPTOR.message_types_by_name['ServiceOptions'] = _SERVICEOPTIONS
  DESCRIPTOR.message_types_by_name['MethodOptions'] = _METHODOPTIONS
  DESCRIPTOR.message_types_by_name['UninterpretedOption'] = _UNINTERPRETEDOPTION
  DESCRIPTOR.message_types_by_name['FeatureSet'] = _FEATURESET
  DESCRIPTOR.message_types_by_name['FeatureSetDefaults'] = _FEATURESETDEFAULTS
  DESCRIPTOR.message_types_by_name['SourceCodeInfo'] = _SOURCECODEINFO
  DESCRIPTOR.message_types_by_name['GeneratedCodeInfo'] = _GENERATEDCODEINFO
  DESCRIPTOR.enum_types_by_name['Edition'] = _EDITION
  _sym_db.RegisterFileDescriptor(DESCRIPTOR)

else:
  _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'google.protobuf.descriptor_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  _globals['DESCRIPTOR']._options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\023com.google.protobufB\020DescriptorProtosH\001Z-google.golang.org/protobuf/types/descriptorpb\370\001\001\242\002\003GPB\252\002\032Google.Protobuf.Reflection'
  _globals['_EXTENSIONRANGEOPTIONS'].fields_by_name['declaration']._options = None
  _globals['_EXTENSIONRANGEOPTIONS'].fields_by_name['declaration']._serialized_options = b'\210\001\002'
  _globals['_FILEOPTIONS'].fields_by_name['java_generate_equals_and_hash']._options = None
  _globals['_FILEOPTIONS'].fields_by_name['java_generate_equals_and_hash']._serialized_options = b'\030\001'
  _globals['_MESSAGEOPTIONS'].fields_by_name['deprecated_legacy_json_field_conflicts']._options = None
  _globals['_MESSAGEOPTIONS'].fields_by_name['deprecated_legacy_json_field_conflicts']._serialized_options = b'\030\001'
  _globals['_ENUMOPTIONS'].fields_by_name['deprecated_legacy_json_field_conflicts']._options = None
  _globals['_ENUMOPTIONS'].fields_by_name['deprecated_legacy_json_field_conflicts']._serialized_options = b'\030\001'
  _globals['_FEATURESET'].fields_by_name['field_presence']._options = None
  _globals['_FEATURESET'].fields_by_name['field_presence']._serialized_options = b'\210\001\001\230\001\004\230\001\001\242\001\r\022\010EXPLICIT\030\346\007\242\001\r\022\010IMPLICIT\030\347\007\242\001\r\022\010EXPLICIT\030\350\007'
  _globals['_FEATURESET'].fields_by_name['enum_type']._options = None
  _globals['_FEATURESET'].fields_by_name['enum_type']._serialized_options = b'\210\001\001\230\001\006\230\001\001\242\001\013\022\006CLOSED\030\346\007\242\001\t\022\004OPEN\030\347\007'
  _globals['_FEATURESET'].fields_by_name['repeated_field_encoding']._options = None
  _globals['_FEATURESET'].fields_by_name['repeated_field_encoding']._serialized_options = b'\210\001\001\230\001\004\230\001\001\242\001\r\022\010EXPANDED\030\346\007\242\001\013\022\006PACKED\030\347\007'
  _globals['_FEATURESET'].fields_by_name['utf8_validation']._options = None
  _globals['_FEATURESET'].fields_by_name['utf8_validation']._serialized_options = b'\210\001\001\230\001\004\230\001\001\242\001\t\022\004NONE\030\346\007\242\001\013\022\006VERIFY\030\347\007'
  _globals['_FEATURESET'].fields_by_name['message_encoding']._options = None
  _globals['_FEATURESET'].fields_by_name['message_encoding']._serialized_options = b'\210\001\001\230\001\004\230\001\001\242\001\024\022\017LENGTH_PREFIXED\030\346\007'
  _globals['_FEATURESET'].fields_by_name['json_format']._options = None
  _globals['_FEATURESET'].fields_by_name['json_format']._serialized_options = b'\210\001\001\230\001\003\230\001\006\230\001\001\242\001\027\022\022LEGACY_BEST_EFFORT\030\346\007\242\001\n\022\005ALLOW\030\347\007'
  _globals['_SOURCECODEINFO_LOCATION'].fields_by_name['path']._options = None
  _globals['_SOURCECODEINFO_LOCATION'].fields_by_name['path']._serialized_options = b'\020\001'
  _globals['_SOURCECODEINFO_LOCATION'].fields_by_name['span']._options = None
  _globals['_SOURCECODEINFO_LOCATION'].fields_by_name['span']._serialized_options = b'\020\001'
  _globals['_GENERATEDCODEINFO_ANNOTATION'].fields_by_name['path']._options = None
  _globals['_GENERATEDCODEINFO_ANNOTATION'].fields_by_name['path']._serialized_options = b'\020\001'
  _globals['_EDITION']._serialized_start=11258
  _globals['_EDITION']._serialized_end=11492
  _globals['_FILEDESCRIPTORSET']._serialized_start=53
  _globals['_FILEDESCRIPTORSET']._serialized_end=130
  _globals['_FILEDESCRIPTORPROTO']._serialized_start=133
  _globals['_FILEDESCRIPTORPROTO']._serialized_end=797
  _globals['_DESCRIPTORPROTO']._serialized_start=800
  _globals['_DESCRIPTORPROTO']._serialized_end=1625
  _globals['_DESCRIPTORPROTO_EXTENSIONRANGE']._serialized_start=1446
  _globals['_DESCRIPTORPROTO_EXTENSIONRANGE']._serialized_end=1568
  _globals['_DESCRIPTORPROTO_RESERVEDRANGE']._serialized_start=1570
  _globals['_DESCRIPTORPROTO_RESERVEDRANGE']._serialized_end=1625
  _globals['_EXTENSIONRANGEOPTIONS']._serialized_start=1628
  _globals['_EXTENSIONRANGEOPTIONS']._serialized_end=2211
  _globals['_EXTENSIONRANGEOPTIONS_DECLARATION']._serialized_start=1998
  _globals['_EXTENSIONRANGEOPTIONS_DECLARATION']._serialized_end=2146
  _globals['_EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE']._serialized_start=2148
  _globals['_EXTENSIONRANGEOPTIONS_VERIFICATIONSTATE']._serialized_end=2200
  _globals['_FIELDDESCRIPTORPROTO']._serialized_start=2214
  _globals['_FIELDDESCRIPTORPROTO']._serialized_end=3047
  _globals['_FIELDDESCRIPTORPROTO_TYPE']._serialized_start=2668
  _globals['_FIELDDESCRIPTORPROTO_TYPE']._serialized_end=2978
  _globals['_FIELDDESCRIPTORPROTO_LABEL']._serialized_start=2980
  _globals['_FIELDDESCRIPTORPROTO_LABEL']._serialized_end=3047
  _globals['_ONEOFDESCRIPTORPROTO']._serialized_start=3049
  _globals['_ONEOFDESCRIPTORPROTO']._serialized_end=3148
  _globals['_ENUMDESCRIPTORPROTO']._serialized_start=3151
  _globals['_ENUMDESCRIPTORPROTO']._serialized_end=3506
  _globals['_ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE']._serialized_start=3447
  _globals['_ENUMDESCRIPTORPROTO_ENUMRESERVEDRANGE']._serialized_end=3506
  _globals['_ENUMVALUEDESCRIPTORPROTO']._serialized_start=3509
  _globals['_ENUMVALUEDESCRIPTORPROTO']._serialized_end=3640
  _globals['_SERVICEDESCRIPTORPROTO']._serialized_start=3643
  _globals['_SERVICEDESCRIPTORPROTO']._serialized_end=3810
  _globals['_METHODDESCRIPTORPROTO']._serialized_start=3813
  _globals['_METHODDESCRIPTORPROTO']._serialized_end=4078
  _globals['_FILEOPTIONS']._serialized_start=4081
  _globals['_FILEOPTIONS']._serialized_end=5307
  _globals['_FILEOPTIONS_OPTIMIZEMODE']._serialized_start=5232
  _globals['_FILEOPTIONS_OPTIMIZEMODE']._serialized_end=5290
  _globals['_MESSAGEOPTIONS']._serialized_start=5310
  _globals['_MESSAGEOPTIONS']._serialized_end=5810
  _globals['_FIELDOPTIONS']._serialized_start=5813
  _globals['_FIELDOPTIONS']._serialized_end=7138
  _globals['_FIELDOPTIONS_EDITIONDEFAULT']._serialized_start=6563
  _globals['_FIELDOPTIONS_EDITIONDEFAULT']._serialized_end=6653
  _globals['_FIELDOPTIONS_CTYPE']._serialized_start=6655
  _globals['_FIELDOPTIONS_CTYPE']._serialized_end=6702
  _globals['_FIELDOPTIONS_JSTYPE']._serialized_start=6704
  _globals['_FIELDOPTIONS_JSTYPE']._serialized_end=6757
  _globals['_FIELDOPTIONS_OPTIONRETENTION']._serialized_start=6759
  _globals['_FIELDOPTIONS_OPTIONRETENTION']._serialized_end=6844
  _globals['_FIELDOPTIONS_OPTIONTARGETTYPE']._serialized_start=6847
  _globals['_FIELDOPTIONS_OPTIONTARGETTYPE']._serialized_end=7115
  _globals['_ONEOFOPTIONS']._serialized_start=7141
  _globals['_ONEOFOPTIONS']._serialized_end=7313
  _globals['_ENUMOPTIONS']._serialized_start=7316
  _globals['_ENUMOPTIONS']._serialized_end=7653
  _globals['_ENUMVALUEOPTIONS']._serialized_start=7656
  _globals['_ENUMVALUEOPTIONS']._serialized_end=7913
  _globals['_SERVICEOPTIONS']._serialized_start=7916
  _globals['_SERVICEOPTIONS']._serialized_end=8129
  _globals['_METHODOPTIONS']._serialized_start=8132
  _globals['_METHODOPTIONS']._serialized_end=8541
  _globals['_METHODOPTIONS_IDEMPOTENCYLEVEL']._serialized_start=8450
  _globals['_METHODOPTIONS_IDEMPOTENCYLEVEL']._serialized_end=8530
  _globals['_UNINTERPRETEDOPTION']._serialized_start=8544
  _globals['_UNINTERPRETEDOPTION']._serialized_end=8954
  _globals['_UNINTERPRETEDOPTION_NAMEPART']._serialized_start=8880
  _globals['_UNINTERPRETEDOPTION_NAMEPART']._serialized_end=8954
  _globals['_FEATURESET']._serialized_start=8957
  _globals['_FEATURESET']._serialized_end=10233
  _globals['_FEATURESET_FIELDPRESENCE']._serialized_start=9736
  _globals['_FEATURESET_FIELDPRESENCE']._serialized_end=9828
  _globals['_FEATURESET_ENUMTYPE']._serialized_start=9830
  _globals['_FEATURESET_ENUMTYPE']._serialized_end=9885
  _globals['_FEATURESET_REPEATEDFIELDENCODING']._serialized_start=9887
  _globals['_FEATURESET_REPEATEDFIELDENCODING']._serialized_end=9973
  _globals['_FEATURESET_UTF8VALIDATION']._serialized_start=9975
  _globals['_FEATURESET_UTF8VALIDATION']._serialized_end=10042
  _globals['_FEATURESET_MESSAGEENCODING']._serialized_start=10044
  _globals['_FEATURESET_MESSAGEENCODING']._serialized_end=10127
  _globals['_FEATURESET_JSONFORMAT']._serialized_start=10129
  _globals['_FEATURESET_JSONFORMAT']._serialized_end=10201
  _globals['_FEATURESETDEFAULTS']._serialized_start=10236
  _globals['_FEATURESETDEFAULTS']._serialized_end=10618
  _globals['_FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT']._serialized_start=10483
  _globals['_FEATURESETDEFAULTS_FEATURESETEDITIONDEFAULT']._serialized_end=10618
  _globals['_SOURCECODEINFO']._serialized_start=10621
  _globals['_SOURCECODEINFO']._serialized_end=10916
  _globals['_SOURCECODEINFO_LOCATION']._serialized_start=10710
  _globals['_SOURCECODEINFO_LOCATION']._serialized_end=10916
  _globals['_GENERATEDCODEINFO']._serialized_start=10919
  _globals['_GENERATEDCODEINFO']._serialized_end=11255
  _globals['_GENERATEDCODEINFO_ANNOTATION']._serialized_start=11020
  _globals['_GENERATEDCODEINFO_ANNOTATION']._serialized_end=11255
  _globals['_GENERATEDCODEINFO_ANNOTATION_SEMANTIC']._serialized_start=11215
  _globals['_GENERATEDCODEINFO_ANNOTATION_SEMANTIC']._serialized_end=11255
# @@protoc_insertion_point(module_scope)