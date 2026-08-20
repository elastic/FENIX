# Lab staging artifacts for fileless-staging examples (benign payloads only).
KEY ?= fenix

hello_elf.xor: ../hello_elf/hello
	python3 -c "d=open('../hello_elf/hello','rb').read(); k=b'$(KEY)'; open('hello_elf.xor','wb').write(bytes([a^k[i%len(k)] for i,a in enumerate(d)]))"

hello_elf.b64: ../hello_elf/hello
	python3 -c "import base64; open('../hello_elf/hello','rb').read(); d=open('../hello_elf/hello','rb').read(); open('hello_elf.b64','wb').write(base64.b64encode(d))"

all: hello_elf.xor hello_elf.b64

clean:
	rm -f hello_elf.xor hello_elf.b64

.PHONY: all clean
