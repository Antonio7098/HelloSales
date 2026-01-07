import { useEffect, useState } from 'react';
import { ScrollScreen, ScreenHeader, VStack, HStack, Text, Badge, Card, Input, List, ListItem, Button, Section, StatsCards, StatCard } from '../../_components/ui';
import { useProductsStore } from '../stores';
import { Product, formatCurrency } from '../../data/mockData';
import { View, StyleSheet, ScrollView } from 'react-native';
import { theme } from '../../theme';

function ProductListItem({ product, onPress }: { product: Product; onPress: () => void }) {
  const statusColors: Record<string, string> = {
    available: '#059669',
    out_of_stock: '#DC2626',
    discontinued: '#64748B',
  };

  return (
    <ListItem
      title={product.name}
      subtitle={`${product.category} • ${product.sku}`}
      description={product.description}
      rightContent={
        <VStack align="flex-end" spacing="xs">
          <Text weight="semibold" color="success">{formatCurrency(product.price)}</Text>
          <Badge color={statusColors[product.status]} variant="soft">
            {product.status.replace('_', ' ')}
          </Badge>
        </VStack>
      }
      chevron
      onPress={onPress}
    />
  );
}

function ProductDetail({ product, onClose }: { product: Product; onClose: () => void }) {
  return (
    <View style={styles.detailContainer}>
      <ScreenHeader
        title={product.name}
        onBack={onClose}
        rightAction={
          <Button variant="ghost" size="sm" onPress={onClose}>
            ✕
          </Button>
        }
      />
      <ScrollScreen contentContainerStyle={styles.detailContent}>
        <VStack spacing="lg">
          <Card>
            <VStack spacing="md">
              <HStack justify="between">
                <Text color="muted">SKU</Text>
                <Text weight="medium">{product.sku}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Category</Text>
                <Text>{product.category}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Price</Text>
                <Text variant="h4" weight="bold" color="success">{formatCurrency(product.price)}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Stock</Text>
                <Text color={product.stock > 0 ? 'primary' : 'error'}>
                  {product.stock > 0 ? `${product.stock} units` : 'Out of Stock'}
                </Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Status</Text>
                <Badge
                  color={product.status === 'available' ? 'success' : product.status === 'out_of_stock' ? 'error' : 'secondary'}
                >
                  {product.status.replace('_', ' ')}
                </Badge>
              </HStack>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Description</Text>
              <Text color="secondary">{product.description}</Text>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Inventory Value</Text>
              <HStack justify="between">
                <Text color="muted">Total Stock Value</Text>
                <Text variant="h4" weight="bold" color="info">
                  {formatCurrency(product.price * product.stock)}
                </Text>
              </HStack>
            </VStack>
          </Card>

          <HStack spacing="sm">
            <Button variant="secondary" fullWidth>
              Edit Product
            </Button>
            <Button variant="primary" fullWidth>
              Add to Quote
            </Button>
          </HStack>
        </VStack>
      </ScrollScreen>
    </View>
  );
}

export default function ProductsScreen() {
  const { products, filteredProducts, searchQuery, categoryFilter, statusFilter, selectedProduct, isLoading, categories, setSearchQuery, setCategoryFilter, setStatusFilter, selectProduct, loadProducts } = useProductsStore();
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const handleProductPress = (product: Product) => {
    selectProduct(product);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
  };

  if (showDetail && selectedProduct) {
    return <ProductDetail product={selectedProduct} onClose={handleCloseDetail} />;
  }

  const availableProducts = products.filter((p) => p.status === 'available');
  const outOfStockProducts = products.filter((p) => p.status === 'out_of_stock');
  const totalInventory = products.reduce((sum, p) => sum + p.price * p.stock, 0);

  return (
    <ScrollScreen
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      <ScreenHeader title="Products" subtitle={`${products.length} total`} />

      <VStack spacing="md" style={styles.content}>
        <Input
          placeholder="Search products..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          size="md"
        />

        <Section title="Category">
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <HStack spacing="sm" style={{ paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.xs }}>
              {categories.map((category) => (
                <Button
                  key={category}
                  variant={categoryFilter === category ? 'primary' : 'secondary'}
                  size="sm"
                  onPress={() => setCategoryFilter(category)}
                >
                  {category}
                </Button>
              ))}
            </HStack>
          </ScrollView>
        </Section>

        <StatsCards style={styles.statsContainer}>
          <StatCard label="Available" value={availableProducts.length} color="success" />
          <StatCard label="Out of Stock" value={outOfStockProducts.length} color="error" />
          <StatCard label="Inventory" value={formatCurrency(totalInventory).replace('$', '')} color="info" />
        </StatsCards>

        <Section title={`Products (${filteredProducts.length})`}>
          <List variant="inset">
            {filteredProducts.map((product) => (
              <ProductListItem
                key={product.id}
                product={product}
                onPress={() => handleProductPress(product)}
              />
            ))}
          </List>
        </Section>
      </VStack>
    </ScrollScreen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xxl,
  },
  statsContainer: {
    marginTop: theme.spacing.sm,
  },
  detailContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  detailContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xxl,
  },
});
