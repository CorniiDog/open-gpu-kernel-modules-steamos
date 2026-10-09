#!/usr/bin/env python3
"""Exercise the production connector detection body with isolated KMS adapters."""
from pathlib import Path
import subprocess
import tempfile
import sys
source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "kernel-open/nvidia-drm/nvidia-drm-connector.c"
source = source_path.read_text()
start = source.index("static enum drm_connector_status __nv_drm_connector_detect_internal(")
end = source.index("static void __nv_drm_connector_force", start)
body = source[start:end]
start = source.index("static int nv_drm_connector_get_modes(")
end = source.index("static int nv_drm_connector_mode_valid", start)
body += source[start:end]
stubs = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#define NULL ((void *)0)
enum drm_connector_status { connector_status_disconnected, connector_status_connected };
struct drm_encoder { int encoder_type; };
struct nv_drm_encoder { struct drm_encoder base; unsigned int hDisplay; };
struct drm_device { struct { int mutex; int dvi_i_subconnector_property; } mode_config; };
struct drm_connector { struct drm_device *dev; int base; };
struct nv_drm_connector { struct drm_connector base; void *edid; struct nv_drm_encoder *nv_detected_encoder; int type; void *modeset_permission_filep; };
struct NvKmsKapiDynamicDisplayParams { int unused; };
static struct nv_drm_encoder test_encoder;
static bool connected, allocation_failure;
static int edid_clear, revoked, mode_calls, modes_added;
typedef unsigned int NvU32;
typedef int NvBool;
#define NV_FALSE 0
#define DRM_MODE_TYPE_PREFERRED 1
#define NV_DRM_DEV_LOG_ERR(...) ((void)0)
struct nv_drm_device { void *pDevice; };
struct drm_display_mode { int type; };
struct NvKmsKapiDisplayMode { int unused; };
static struct nv_drm_device nv_device;
#define to_nv_device(d) (&nv_device)
static int get_mode(void *d, unsigned int display, unsigned int index, struct NvKmsKapiDisplayMode *mode, NvBool *valid, NvBool *preferred) {
 mode_calls++; assert(display==77); *valid=1; *preferred=1; return index==0 ? 1 : 0;
}
static struct { int (*getDisplayMode)(void *, unsigned int, unsigned int, struct NvKmsKapiDisplayMode *, NvBool *, NvBool *); } kms = { get_mode }, *nvKms = &kms;
static struct drm_display_mode mode;
static struct drm_display_mode *drm_mode_create(struct drm_device *d) { return &mode; }
static void nvkms_display_mode_to_drm_mode(struct NvKmsKapiDisplayMode *a, struct drm_display_mode *b) {}
static void drm_mode_probed_add(struct drm_connector *c, struct drm_display_mode *m) { modes_added++; }
#define to_nv_connector(c) ((struct nv_drm_connector *)(c))
#define to_nv_encoder(e) ((struct nv_drm_encoder *)(e))
#define BUG_ON(x) assert(!(x))
#define WARN_ON(x) ((void)(x))
#define mutex_is_locked(x) (*(x))
#define NVKMS_CONNECTOR_TYPE_DVI_I 1
#define DRM_MODE_ENCODER_DAC 1
#define DRM_MODE_SUBCONNECTOR_DVIA 1
#define DRM_MODE_SUBCONNECTOR_DVID 2
#define nv_drm_connector_for_each_possible_encoder(c,e) for ((e)=&test_encoder.base; (e); (e)=NULL)
#define nv_drm_connector_for_each_possible_encoder_end
static void *nv_drm_calloc(int n, size_t size) { return allocation_failure ? NULL : calloc(n,size); }
static void nv_drm_free(void *p) { free(p); }
static bool __nv_drm_detect_encoder(struct NvKmsKapiDynamicDisplayParams *p, struct drm_connector *c, struct drm_encoder *e) { return connected; }
static void drm_object_property_set_value(void *o, int p, int v) {}
static void nv_drm_connector_update_edid_property(struct drm_connector *c, void *edid) { assert(edid == NULL); edid_clear++; }
static void nv_drm_connector_revoke_permissions(struct drm_device *d, struct nv_drm_connector *c) { revoked++; c->modeset_permission_filep=NULL; }
"""
checks = r"""
int main(void) {
 struct drm_device dev = { .mode_config.mutex = 1 };
 struct nv_drm_connector c = { .base.dev=&dev };
 test_encoder.hDisplay=77;
 connected=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_connected);
 assert(c.nv_detected_encoder==&test_encoder && edid_clear==0);
 assert(nv_drm_connector_get_modes(&c.base)==1 && mode_calls==2 && modes_added==1);
 c.edid=malloc(8); c.modeset_permission_filep=&dev;
 connected=false;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_disconnected);
 assert(c.nv_detected_encoder==NULL && c.edid==NULL && edid_clear==1 && revoked==1);
 assert(nv_drm_connector_get_modes(&c.base)==0 && mode_calls==2);
 connected=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_connected);
 assert(c.nv_detected_encoder==&test_encoder);
 assert(nv_drm_connector_get_modes(&c.base)==1 && mode_calls==4 && modes_added==2);
 allocation_failure=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_disconnected);
 assert(c.nv_detected_encoder==NULL && edid_clear==2);
 assert(nv_drm_connector_get_modes(&c.base)==0 && mode_calls==4);
 return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="opemos-hotplug-test-") as tmp:
 c=Path(tmp)/"test.c"; exe=Path(tmp)/"test"
 c.write_text(stubs+body+checks)
 subprocess.run(["cc", "-std=c99", "-Werror=implicit-function-declaration", str(c), "-o", str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print("PASS: connect, disconnect, reconnect, allocation-failure state, permission cleanup and get_modes NVKMS call guards")
