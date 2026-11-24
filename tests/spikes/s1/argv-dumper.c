/* Inert fixture only; no OS utility, filesystem, network or environment access. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int u32(uint32_t n)
{
    unsigned char b[4] = {(unsigned char)n, (unsigned char)(n >> 8),
        (unsigned char)(n >> 16), (unsigned char)(n >> 24)};
    return fwrite(b, 1, sizeof b, stdout) == sizeof b;
}

int main(int argc, char **argv)
{
    size_t lengths[33];
    size_t total = 0;
    if (argc < 1 || argc > 33) return 2;
    for (int i = 0; i < argc; ++i) {
        const size_t n = strlen(argv[i]);
        if (n > 1024 || n > 32768 - total) return 2;
        lengths[i] = n;
        total += n;
    }
    if (!u32((uint32_t)argc)) return 3;
    for (int i = 0; i < argc; ++i) {
        if (!u32((uint32_t)lengths[i]) ||
            fwrite(argv[i], 1, lengths[i], stdout) != lengths[i]) return 3;
    }
    return fflush(stdout) == 0 ? 0 : 3;
}
