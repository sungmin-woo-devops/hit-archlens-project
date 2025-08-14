jq -r '
  ["group","service","service_url"],
  (.items[]
   | select(.tags | map(select(.tagNamespaceId=="aws-products#type" and .name=="Service")) | length>0)
   | [.item.additionalFields.productCategory,
      .item.additionalFields.productName,
      .item.additionalFields.productUrl]
  )
  | @csv
' aws_products.json > aws_services.csv
