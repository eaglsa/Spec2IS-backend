def paginate_api(client, url, params=None, offset_param='offset', limit_param='limit', limit=10, data_key='data'):
    """Generic pagination for JSON APIs."""
    if params is None:
        params = {}
        
    offset = 0
    while True:
        params[offset_param] = offset
        params[limit_param] = limit
        
        response = client.get(url, params=params)
        data = response.json()
        
        items = data.get(data_key, [])
        if not items:
            break
            
        for item in items:
            yield item
            
        offset += limit
        
        # Adjust condition if total count is available
        total = data.get('total')
        if total is not None and offset >= total:
            break
        
        if len(items) < limit:
            break
