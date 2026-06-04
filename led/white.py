from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver

strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=121).get_strip()
strip.set_brightness(0.1)             # keep low unless your PSU is 4A+

for i in range(0, 121):                 # 0..120, drive ALL pixels incl. pixel 0
    strip.set_pixel_color(i, Color(255, 255, 255))
strip.show()