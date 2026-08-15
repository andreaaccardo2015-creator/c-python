import finityengine

// Script del modello "player".
//
// In FinityEngine ogni script e' figlio di un modello: non si dichiara nessun
// actor, non si apre nessuna finestra (ci pensa l'editor quando fai la build) e
// il soggetto di ogni chiamata e' il modello a cui lo script e' attaccato.
// Uno script tocca solo se stesso: il muro e la moneta hanno il proprio.
//
// Le animazioni ("camminata", "colpito") sono assegnate al modello nell'editor:
// qui lo script le avvia e le ferma per nome.
//
// Un solo on start, un solo on fixedupdate, un solo on update.

on start {
    animation.start("camminata")
}

on fixedupdate {
    // dt qui vale sempre 1/60: la velocita' non cambia con gli FPS
    float speed 240f
    if (finityengine.Input.GetKey("d") or finityengine.Input.GetKey("right")) {
        move(speed * dt, 0)
    }
    if (finityengine.Input.GetKey("a") or finityengine.Input.GetKey("left")) {
        move(0 - speed * dt, 0)
    }
    if (finityengine.Input.GetKey("w") or finityengine.Input.GetKey("up")) {
        move(0, 0 - speed * dt)
    }
    if (finityengine.Input.GetKey("s") or finityengine.Input.GetKey("down")) {
        move(0, speed * dt)
    }
}

on update {
    // getcollision chiede "io tocco quello?": l'io e' il modello di questo script
    if (getcollision "muro") {
        animation.start("colpito")
    } else {
        animation.start("camminata")
    }
}
