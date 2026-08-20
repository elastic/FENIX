CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -fPIC

hello_so.so: hello_so.c
	$(CC) $(CFLAGS) -shared -o hello_so.so hello_so.c

clean:
	rm -f hello_so.so

.PHONY: clean
