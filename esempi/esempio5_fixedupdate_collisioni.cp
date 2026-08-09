// Esempio 5 — on fixedupdate, getcollision e animazioni
// Muoviti con WASD/frecce: il player diventa rosso quando tocca il muro.
import screen
import finityengine

screen.create(800, 600, "C Python - fixedupdate, collisioni, animazioni")

actor muro

on start {
    muro.transform.position == x 520; y 240;
    muro.width = 60
    muro.height = 120
    muro.ActorColor(#8D6E63)
}

actor moneta

on start {
    moneta.transform.position == x 100; y 80;
    moneta.width = 24
    moneta.height = 24
    moneta.ActorColor(#FFD54F)
    // animazione di proprieta': la x va da 100 a 700 in 3 secondi
    moneta.animate("x", 100, 700, 3)
}

actor player

on start {
    player.transform.position == x 380; y 280;
    player.width = 48
    player.height = 48
    player.ActorColor(#4FC3F7)
    // Con un'immagine:      player.sprite("hero.png")
    // Con uno sprite sheet: player.animation("run", "run.png", 6, 12)
    //                       player.play("run")
}

on fixedupdate {
    // Qui dt e' SEMPRE fisso (finityengine.Time.fixedDeltaTime, default 1/60):
    // il movimento resta identico anche se gli FPS ballano.
    float speed = 220
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

on update {
    // Logica a frame variabile: colore in base alle collisioni
    if (getcollision "muro") {
        player.ActorColor(#E57373)
    } else {
        player.ActorColor(#4FC3F7)
    }
    if (getcollision "moneta") {
        moneta.active = false
    }
}

finityengine.Run()
