drserv is an authenticated HTTP API for publishing .deb package to a repo

## API Usage

This service makes one endpoint available:

```
/v1/publish/{major.dist}/{minor.dist}/{component}/{filename.deb}
```

`major.dist` indicates the code name of the target Debian type distribution,
a string such as `squeeze` or `trusty`.

`minor.dist` is a somewhat special concept where different users of
a repository for a specific upstream Debian type distribution wants slightly
different versions of packages. Typical values of this part is `stable`,
`testing` or `unstable`.

`component` corresponds to the component concept in the upstream structure 
as documented in the [RepositoryFormat] and would be a string such as `main`
or `non-free`.

The content of the deb file to be published is to be provided as POST body
data.





[RepositoryFormat]: https://wiki.debian.org/RepositoryFormat





