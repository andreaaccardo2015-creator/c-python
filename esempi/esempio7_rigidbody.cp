import finityengine

// Script collegato all'intera scena, non a un singolo modello: per questo i
// modelli vanno nominati per intero, come "player".
//
// rigidbody.call("RB") collega il rigidbody e lo rende raggiungibile come
// player.RB. Maiuscole e minuscole non contano, quindi player.rb va bene
// uguale, e vale anche per "trasform" scritto senza la n.

rigidbody.call("RB")

on start {
    // alza il braccio di 5 sull'asse y, subito
    player.rb.trasform.part("braccio", y += 5)
}

on update {
    if (finityengine.Input.GetKeyDown("space")) {
        // ogni pressione somma: due volte fanno 10
        player.rb.trasform.part("braccio", y += 5)
    }

    if (finityengine.Input.GetKeyDown("r")) {
        // con "=" il numero e' una posizione, non uno spostamento: torna a zero
        player.rb.trasform.part("braccio", y = 0)
    }

    if (finityengine.Input.GetKeyDown("t")) {
        // due assi in una riga, e l'ultimo numero e' la durata in secondi:
        // la testa arriva a destinazione in mezzo secondo invece che di colpo
        player.rb.trasform.part("testa", y += 90, x -= 10, 0.5f)
    }
}
