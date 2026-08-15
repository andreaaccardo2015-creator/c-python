// Esempio JIT — funzioni pure numeriche accelerate dal backend C++/LLVM
// Esegui: python -m cpython --jit esempi/esempio4_jit_math.cp

fun add(int a, int b)
    return int a + b

fun muladd(int a, int b, int c)
    return int a * b + c

fun factorial(int n)
    int r 1
    int i 1
    while (i <= n)
        r = r * i
        i = i + 1
    return int r

fun absdiff(float x, float y)
    float d x - y
    if (d < 0)
        return float 0 - d
    return float d

int somma add(2, 5)
print.output("2 + 5 fa:", somma)

int m muladd(3, 4, 1)
print.output("3 * 4 + 1 fa:", m)

int fatt factorial(6)
print.output("6! fa:", fatt)

float scarto absdiff(10.5f, 3.25f)
print.output("scarto:", scarto)
