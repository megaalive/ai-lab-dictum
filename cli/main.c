#include <stdio.h>
#include <string.h>

#include "proposal.h"

enum {
    EXIT_OK = 0,
    EXIT_IO_ERROR = 1,
    EXIT_INVALID_ARGUMENTS = 2,
    EXIT_UNSUPPORTED = 3,
    EXIT_EXECUTION_DENIED = 4
};

static const char help[] =
    "Dictum - fondasi runtime lokal\n"
    "\n"
    "  dictum --help           Tampilkan bantuan.\n"
    "  dictum --version        Tampilkan versi.\n"
    "  dictum ask \"instruksi\"  Terjemahan belum tersedia.\n"
    "  dictum run \"instruksi\"  Eksekusi dinonaktifkan.\n";

static const char invalid_arguments[] =
    "dictum: argumen tidak valid. Gunakan --help.\n";

static int report(FILE *stream, const char *message, int status)
{
    if (fputs(message, stream) == EOF || fflush(stream) == EOF) {
        return EXIT_IO_ERROR;
    }
    return status;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        return report(stderr, invalid_arguments, EXIT_INVALID_ARGUMENTS);
    }

    const char *command = argv[1];
    if (strcmp(command, "run") == 0) {
        return report(stderr, "dictum: eksekusi ditolak (proposal-only).\n",
                      EXIT_EXECUTION_DENIED);
    }
    if (argc == 2 && strcmp(command, "--help") == 0) {
        return report(stdout, help, EXIT_OK);
    }
    if (argc == 2 && strcmp(command, "--version") == 0) {
        return report(stdout, "dictum " DICTUM_VERSION "\n", EXIT_OK);
    }
    if (argc == 3 && strcmp(command, "ask") == 0 &&
        dictum_propose(argv[2]) == DICTUM_PROPOSAL_UNSUPPORTED) {
        return report(stderr, "dictum: unsupported. Terjemahan instruksi belum tersedia.\n",
                      EXIT_UNSUPPORTED);
    }
    return report(stderr, invalid_arguments, EXIT_INVALID_ARGUMENTS);
}
