PLATFORM ?= esp8266

REPO_ROOT = $(abspath ../..)
MJS_PATH = $(REPO_ROOT)/mjs
LIBS_PATH = $(REPO_ROOT)/mos_libs

EXAMPLES_cc3200 = c_aws_shadow c_binary_lib c_hello c_mqtt c_network c_no_libs
EXAMPLES_esp32 =  c_aws_shadow c_binary_lib c_hello c_mqtt c_network c_no_libs
EXAMPLES_esp8266 = c_aws_shadow c_binary_lib c_heater c_hello c_mqtt c_network c_no_libs
EXAMPLES_pic32 =
EXAMPLES_stm32 =

MOS ?= mos

$(eval EXAMPLES=$(EXAMPLES_$(PLATFORM)))

.PHONY: all $(EXAMPLES) list_examples

export PLATFORM

all: $(EXAMPLES)

$(EXAMPLES): $(MJS_PATH)/mjs.c $(MJS_PATH)/mjs.h
	@echo "=== Building $@ / $(PLATFORM)"
	@cd $@ && $(MOS) build --local --clean --arch $(PLATFORM) \
		--repo $(REPO_ROOT) \
		--libs-dir $(LIBS_PATH) --no-libs-update \
		--module mjs:$(MJS_PATH) \

$(MJS_PATH)/mjs.c $(MJS_PATH)/mjs.h:
	@echo "=== Creating $@"
	@make -C $(MJS_PATH) $(notdir $@)

clean:
	echo "TODO: add mgos clean"
	@for d in $(EXAMPLES) ; do \
	  rm -rf $$d/build; \
	done

list_examples:
	@echo $(EXAMPLES)
