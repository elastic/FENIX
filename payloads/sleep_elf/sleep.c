#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    unsigned int seconds = 60;

    if (argc > 1) {
        char *end = NULL;
        long val = strtol(argv[1], &end, 10);
        if (end != argv[1] && *end == '\0' && val > 0)
            seconds = (unsigned int)val;
    }

    printf("fenix sleep payload: sleeping for %u seconds\n", seconds);
    sleep(seconds);
    return 0;
}
