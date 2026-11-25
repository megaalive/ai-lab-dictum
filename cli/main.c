#include <stdio.h>
#include <string.h>
#include <time.h>
#include "pipeline.h"

enum { EXIT_OK=0, EXIT_IO_ERROR=1, EXIT_INVALID_ARGUMENTS=2,
       EXIT_UNSUPPORTED=3, EXIT_EXECUTION_DENIED=4, EXIT_CLARIFY=5, EXIT_INTERNAL=6 };

static const char help[] =
    "Dictum - F1 catalog / synthetic proposal-only\n"
    "  dictum ask \"instruksi\"      Usulan terstruktur, tanpa eksekusi.\n"
    "  dictum explain \"instruksi\" Penjelasan usulan stateless.\n"
    "  dictum search intent.id     Cari ID katalog (48 intent).\n"
    "  dictum inspect              Identitas katalog dan status.\n"
    "  dictum run                  Eksekusi dinonaktifkan.\n";
static const char invalid_arguments[]="dictum: argumen tidak valid. Gunakan --help.\n";

static int report(FILE *stream,const char *message,int status)
{
    if (fputs(message,stream)==EOF || fflush(stream)==EOF) return EXIT_IO_ERROR;
    return status;
}
static int json_report(const char *message,int status)
{
    if (puts(message)==EOF || fflush(stdout)==EOF) return EXIT_IO_ERROR;
    return status;
}
static int ask(const char *text)
{
    const size_t size=strlen(text);
    if (size==0) return report(stderr,invalid_arguments,EXIT_INVALID_ARGUMENTS);
    const time_t now=time(NULL);
    if (now==(time_t)-1) return report(stderr,"dictum: internal error.\n",EXIT_INTERNAL);
    struct pipeline_result result;
    if (!pipeline_run((const unsigned char *)text,size,(int64_t)now,1,PIPE_B0,&result))
        return report(stderr,"dictum: internal error.\n",EXIT_INTERNAL);
    int status;
    switch (result.outcome) {
    case PIPE_PROPOSAL: status=EXIT_OK; break;
    case PIPE_CLARIFY: status=EXIT_CLARIFY; break;
    case PIPE_UNSUPPORTED: status=EXIT_UNSUPPORTED; break;
    case PIPE_DENY: status=EXIT_EXECUTION_DENIED; break;
    case PIPE_INTERNAL: default: return report(stderr,"dictum: internal error.\n",EXIT_INTERNAL);
    }
    return json_report(result.view,status);
}
int main(int argc,char *argv[])
{
    if (argc<2) return report(stderr,invalid_arguments,EXIT_INVALID_ARGUMENTS);
    const char *command=argv[1];
    if (strcmp(command,"run")==0)
        return report(stderr,"dictum: eksekusi ditolak (proposal-only).\n",EXIT_EXECUTION_DENIED);
    if (argc==2 && strcmp(command,"--help")==0) return report(stdout,help,EXIT_OK);
    if (argc==2 && strcmp(command,"--version")==0) return report(stdout,"dictum " DICTUM_VERSION "\n",EXIT_OK);
    char out[PIPE_FRAME];
    if (argc==2 && strcmp(command,"inspect")==0) {
        if (!pipeline_inspect(out)) return report(stderr,"dictum: internal error.\n",EXIT_INTERNAL);
        return json_report(out,EXIT_OK);
    }
    if (argc==3 && strcmp(command,"search")==0) {
        if (!pipeline_search(argv[2],out)) return report(stderr,"dictum: unsupported intent.\n",EXIT_UNSUPPORTED);
        return json_report(out,EXIT_OK);
    }
    if (argc==3 && (strcmp(command,"ask")==0 || strcmp(command,"explain")==0)) return ask(argv[2]);
    /* Shorthand only for a phrase, not unknown options or bare CLI verbs. */
    if (argc==2 && command[0]!='-' && strchr(command,' ')!=NULL) return ask(command);
    return report(stderr,invalid_arguments,EXIT_INVALID_ARGUMENTS);
}
