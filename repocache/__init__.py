
# Copyright (C) 2011 Javier Palacios
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License Version 2
# as published by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.


import urllib2

from cache import *
import repolib.config

source_url = {}


def load_confs () :
    for repo in repolib.config.get_all_configs( 'type' , 'deb' ) :
        source_url[ repo.name ] = repo['url']


def handler ( req ) :

    local_path = req.filename
    _subpath = local_path.replace( req.hlist.directory , "" , 1 )
    # FIXME : top directory (debian) must be created by hand or an error happens
    reponame , subpath = _subpath.split("/",1)
    if not source_url.has_key( reponame ) :
        req.log_error( "Reloading configurations" )
        load_confs()
    remote_url = source_url[reponame]

    if req.used_path_info :
        local_path += req.path_info
        remote_url = urllib2.urlparse.urljoin( remote_url , subpath + req.path_info )

    return get_file( req , local_path , remote_url )


load_confs()

