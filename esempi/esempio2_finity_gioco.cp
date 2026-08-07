// Mini gioco FinityEngine — lo script è allocato all'Actor "player"
import screen
import finityengine
import time
import random

screen.create(800, 600, "C python + finity engine")
// oppure: screen.create(fullscreen, "C python + finity engine")

actor player

on start {
    player.transform.position == x 380; y 280;
    player.ActorColor(#FFB74D)
    player.width set 48
    player.height = 48
    // le collisioni sono precompilate (width/height)
}

on update {
    float speed = 220
    float dt = finityengine.Time.deltaTime
    if (finityengine.Input.GetKey("d") or finityengine.Input.GetKey("right")) {
        player.move(speed * dt, 0)
    }
    if (finityengine.Input.GetKey("a") or finityengine.Input.GetKey("left")) {
        player.move(0 - speed * dt, 0)
    }
    if (finityengine.Input.GetKey("w") or finityengine.Input.GetKey("up")) {
        player.move(0, 0 - speed * dt)
    }
    if (finityengine.Input.GetKey("s") or finityengine.Input.GetKey("down")) {
        player.move(0, speed * dt)
    }
}

finityengine.Run()
