obj-m += hello_lkm.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

hello_lkm.ko: hello_lkm.c
	$(MAKE) -C $(KDIR) M=$(PWD) modules

hello_lkm_embed.h: hello_lkm.ko
	xxd -i $< > $@

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f hello_lkm_embed.h

.PHONY: clean embed
embed: hello_lkm_embed.h
