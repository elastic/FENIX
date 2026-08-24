/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * hello_lkm — Benign test kernel module for FENIX lab use.
 * Logs on load and unload. No hooks, persistence, or stealth.
 * GPL-2.0-only because it includes Linux kernel headers.
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("FENIX");
MODULE_DESCRIPTION("Benign hello-world test module for FENIX lab PoCs");
MODULE_VERSION("0.1");

static int __init hello_lkm_init(void)
{
    pr_info("hello_lkm: loaded (hello from fenix)\n");
    return 0;
}

static void __exit hello_lkm_exit(void)
{
    pr_info("hello_lkm: unloaded\n");
}

module_init(hello_lkm_init);
module_exit(hello_lkm_exit);
