#ifndef _ZYPP_UTILS_H_
#define _ZYPP_UTILS_H_

#include <stdlib.h>
#include <glib.h>
#include <zypp/RepoManager.h>
#include <zypp/media/MediaManager.h>
#include <zypp/Resolvable.h>
#include <zypp/ResPool.h>

#include <list>
#include <set>

// some typedefs and functions to shorten Zypp names
typedef zypp::ResPoolProxy ZyppPool;
//inline ZyppPool zyppPool() { return zypp::getZYpp()->poolProxy(); }
typedef zypp::ui::Selectable::Ptr ZyppSelectable;
typedef zypp::ui::Selectable*		ZyppSelectablePtr;
typedef zypp::ResObject::constPtr	ZyppObject;
typedef zypp::Package::constPtr		ZyppPackage;
typedef zypp::Patch::constPtr		ZyppPatch;
typedef zypp::Pattern::constPtr		ZyppPattern;
typedef zypp::Language::constPtr	ZyppLanguage;
//inline ZyppPackage tryCastToZyppPkg (ZyppObject obj)
//	{ return zypp::dynamic_pointer_cast <const zypp::Package> (obj); }
typedef std::set<zypp::PoolItem_Ref> Candidates;

zypp::ZYpp::Ptr get_zypp ();

gboolean zypp_is_changeable_media (const zypp::Url &url);

/**
 * Build and return a ResPool that contains all local resolvables
 * and ones found in the enabled repositories.
 */
zypp::ResPool zypp_build_pool (gboolean include_local);

/**
 * Returns a list of packages that match the specified package_name.
 */
std::vector<zypp::PoolItem> * zypp_get_packages_by_name (const gchar *package_name, gboolean include_local);

/**
 * Returns the Resolvable for the specified package_id.
 */
zypp::Resolvable::constPtr zypp_get_package_by_id (const gchar *package_id);

/**
 * Build a package_id from the specified resolvable.  The returned
 * gchar * should be freed with g_free ().
 */
gchar * zypp_build_package_id_from_resolvable (zypp::Resolvable::constPtr resolvable);

void zypp_emit_packages_in_list (PkBackend *backend, std::vector<zypp::PoolItem> *v);
#endif // _ZYPP_UTILS_H_

