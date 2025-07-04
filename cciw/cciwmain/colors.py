from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Color:
    """
    RGB color, components from 0 to 255
    """

    red: int
    green: int
    blue: int

    def __post_init__(self):
        assert 0 <= self.red <= 255
        assert 0 <= self.green <= 255
        assert 0 <= self.blue <= 255

    @classmethod
    def from_rgb_string(cls, rgb_string) -> Color:
        assert rgb_string[0] == "#"
        rgb = rgb_string[1:]
        red, green, blue = rgb[0:2], rgb[2:4], rgb[4:6]
        return cls(red=int(red, 16), green=int(green, 16), blue=int(blue, 16))

    def to_rgb_string(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


def brightness(color: Color) -> float:
    """
    Computes the "brightness" of a color
    """

    # Brightness is similiar to lightness in HSL but more closely approximates
    # how humans perceive the intensity of the different RGB components of
    # a color. Brightness is sometimes called luminance.
    #
    # Returns a number between 0 and 1, where 1 is fully bright
    # (white) and 0 is fully dark (black) for color values.
    #
    return ((color.red * 0.299) + (color.green * 0.587) + (color.blue * 0.114)) / 255


WHITE = Color.from_rgb_string("#ffffff")
BLACK = Color.from_rgb_string("#000000")


def contrast_color(color: Color, light=WHITE, dark=BLACK) -> Color:
    color_brightness = brightness(color)
    dark_brightness = brightness(BLACK)
    light_brightness = brightness(WHITE)

    return light if (abs(color_brightness - light_brightness) > abs(color_brightness - dark_brightness)) else dark
