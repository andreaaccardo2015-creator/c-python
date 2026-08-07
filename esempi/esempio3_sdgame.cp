// Esempio sdgame — gioco 2D senza FinityEngine (stile pygame)
import sdgame
import math

sdgame.init(640, 480, "sdgame demo")

float x = 100
float y = 100
float speed = 200

while (sdgame.is_running()) {
    sdgame.tick(60)

    if (sdgame.getkey("d") or sdgame.getkey("right")) {
        x = x + speed * sdgame.dt()
    }
    if (sdgame.getkey("a") or sdgame.getkey("left")) {
        x = x - speed * sdgame.dt()
    }
    if (sdgame.getkey("s") or sdgame.getkey("down")) {
        y = y + speed * sdgame.dt()
    }
    if (sdgame.getkey("w") or sdgame.getkey("up")) {
        y = y - speed * sdgame.dt()
    }

    x = math.clamp(x, 0, sdgame.width() - 40)
    y = math.clamp(y, 0, sdgame.height() - 40)

    sdgame.fill(#1A1F2B)
    sdgame.rect(x, y, 40, 40, #FFB74D)
    sdgame.text("WASD / frecce per muoverti", 16, 16, #FFFFFF, 22)
    sdgame.flip()
}

sdgame.quit()
