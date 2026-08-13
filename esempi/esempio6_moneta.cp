import finityengine

// Script del modello "moneta", da leggere insieme a esempio6_player.cp.
//
// Mostra come controllare un'animazione a tempo: animation.time "N" diventa
// vera quando l'animazione in corso raggiunge il secondo N dal suo inizio.

on start {
    animation.start("gira")
}

on update {
    // "gira" dura 3 secondi: la fermo a 2, cioe' a un terzo dalla fine
    if (animation.time "2") {
        animation.stop("gira")
    }
}
