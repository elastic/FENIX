CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -Ihelpers

BIN_DIR := bin
HELPERS := fenix-memfd-exec fenix-memfd-script-exec fenix-memfd-self-reexec \
	fenix-memfd-so-load fenix-shm-exec fenix-shm-so-load fenix-stdin-memexec \
	fenix-pipe-exec fenix-proc-fd-exec fenix-lolbin-fd-exec \
	fenix-deleted-exec fenix-init-module fenix-finit-module fenix-embedded-init-module

.PHONY: all helpers payloads clean

all: payloads helpers

# Payloads first: fenix-embedded-init-module needs hello_lkm.ko → hello_lkm_embed.h
helpers: $(BIN_DIR) $(addprefix $(BIN_DIR)/,$(HELPERS))

payloads/hello_lkm/hello_lkm.ko:
	$(MAKE) -C payloads/hello_lkm hello_lkm.ko

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/fenix-memfd-exec: helpers/fenix-memfd-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-memfd-script-exec: helpers/fenix-memfd-script-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-memfd-self-reexec: helpers/fenix-memfd-self-reexec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-memfd-so-load: helpers/fenix-memfd-so-load.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -ldl -o $@ $<

$(BIN_DIR)/fenix-shm-exec: helpers/fenix-shm-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-shm-so-load: helpers/fenix-shm-so-load.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -ldl -o $@ $<

$(BIN_DIR)/fenix-stdin-memexec: helpers/fenix-stdin-memexec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-pipe-exec: helpers/fenix-pipe-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-proc-fd-exec: helpers/fenix-proc-fd-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-lolbin-fd-exec: helpers/fenix-lolbin-fd-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-deleted-exec: helpers/fenix-deleted-exec.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-init-module: helpers/fenix-init-module.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN_DIR)/fenix-finit-module: helpers/fenix-finit-module.c | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $<

payloads/hello_lkm/hello_lkm_embed.h: payloads/hello_lkm/hello_lkm.ko
	$(MAKE) -C payloads/hello_lkm hello_lkm_embed.h

$(BIN_DIR)/fenix-embedded-init-module: helpers/fenix-embedded-init-module.c payloads/hello_lkm/hello_lkm_embed.h | $(BIN_DIR)
	$(CC) $(CFLAGS) -Ipayloads/hello_lkm -o $@ helpers/fenix-embedded-init-module.c

payloads:
	$(MAKE) -C payloads/hello_elf
	$(MAKE) -C payloads/sleep_elf
	$(MAKE) -C payloads/hello_lkm
	$(MAKE) -C payloads/hello_lkm embed
	$(MAKE) -C payloads/hello_so
	$(MAKE) -C payloads/staged

clean:
	rm -rf $(BIN_DIR)
	$(MAKE) -C payloads/hello_elf clean
	$(MAKE) -C payloads/sleep_elf clean
	$(MAKE) -C payloads/hello_lkm clean
	$(MAKE) -C payloads/hello_so clean
	$(MAKE) -C payloads/staged clean
