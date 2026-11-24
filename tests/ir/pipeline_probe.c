/* Synthetic-only inspection executable. Not part of the product CLI. */
#include "pipeline.h"
#include "ir_wire.h"
#include <stdio.h>
#include <string.h>
int main(int argc,char *argv[])
{
    if (argc!=2) return 2;
    enum pipeline_model model;
    if (strcmp(argv[1],"B0")==0) model=PIPE_B0;
    else if (strcmp(argv[1],"B1")==0) model=PIPE_B1;
    else return 2;
    unsigned char data[DICTUM_INPUT_MAX+1u];
    const size_t size=fread(data,1,sizeof(data),stdin);
    if (ferror(stdin)) return 2;
    struct pipeline_result p;
    if (!pipeline_run(data,size,INT64_C(1760000600),1,model,&p)) return 2;
    printf("{\"context\":%s,\"nlu\":%s,\"ir\":%s,\"policy\":%s,\"plan\":%s,\"view\":%s}\n",
        p.context[0]=='\0'?"null":p.context,p.nlu[0]=='\0'?"null":p.nlu,
        p.ir[0]=='\0'?"null":p.ir,p.policy[0]=='\0'?"null":p.policy,
        p.plan[0]=='\0'?"null":p.plan,p.view);
    return ferror(stdout)||fflush(stdout)==EOF ? 2 : 0;
}
