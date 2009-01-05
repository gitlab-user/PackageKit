// apt.h  -*-c++-*-
//
//  Copyright 1999-2002, 2004-2005, 2007-2008 Daniel Burrows
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation; either version 2 of the License, or
//  (at your option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with this program; see the file COPYING.  If not, write to
//  the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
//  Boston, MA 02111-1307, USA.
//

#ifndef APT_H
#define APT_H

#include <apt-pkg/depcache.h>
#include <apt-pkg/pkgrecords.h>
#include <apt-pkg/sourcelist.h>
#include <apt-pkg/pkgcachegen.h>

#include <packagekit-glib/packagekit.h>
#include <pk-backend.h>

#include <string>

/** \return a short description string corresponding to the given
*  version.
*/
void emit_package (PkBackend *backend, pkgRecords *records, PkBitfield filters,
		   const pkgCache::PkgIterator &pkg,
		   const pkgCache::VerIterator &ver);

void emit_details (PkBackend *backend, pkgRecords *records,
		   const pkgCache::PkgIterator &pkg,
		   const pkgCache::VerIterator &ver);

void emit_requires (PkBackend *backend, pkgRecords *records, PkBitfield filters,
		   const pkgCache::PkgIterator &pkg,
		   const pkgCache::VerIterator &ver);

class apt_init
{
public:
	apt_init(const char *locale, pkgSourceList &apt_source_list);
	~apt_init();

	pkgRecords    *packageRecords;
	pkgCache      *cacheFile;
	MMap          *Map;
};

#endif