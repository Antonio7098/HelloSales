import { useEffect, useState } from 'react';
import { ScrollScreen, ScreenHeader, VStack, HStack, Text, Badge, Card, Input, List, ListItem, Button, Section, StatsCards, StatCard } from '../../_components/ui';
import { useSalesRepsStore } from '../stores';
import { SalesRep, formatCurrency, formatPercent } from '../../data/mockData';
import { View, StyleSheet, ScrollView } from 'react-native';
import { theme } from '../../theme';

function SalesRepListItem({ salesRep, onPress }: { salesRep: SalesRep; onPress: () => void }) {
  const performanceColor = salesRep.performance >= 100 ? 'success' : salesRep.performance >= 80 ? 'warning' : 'error';
  const statusColor = salesRep.status === 'active' ? 'success' : 'secondary';

  return (
    <ListItem
      title={salesRep.name}
      subtitle={`${salesRep.territory} • ${salesRep.clients} clients`}
      description={`Sales: ${formatCurrency(salesRep.totalSales)} • Target: ${formatCurrency(salesRep.target)}`}
      rightContent={
        <VStack align="flex-end" spacing="xs">
          <Text weight="semibold" color={performanceColor}>
            {formatPercent(salesRep.performance)} of target
          </Text>
          <Badge color={statusColor} variant="soft">
            {salesRep.status}
          </Badge>
        </VStack>
      }
      chevron
      onPress={onPress}
    />
  );
}

function SalesRepDetail({ salesRep, onClose }: { salesRep: SalesRep; onClose: () => void }) {
  const progress = Math.min(salesRep.totalSales / salesRep.target, 1);
  const performanceColor = salesRep.performance >= 100 ? '#059669' : salesRep.performance >= 80 ? '#D97706' : '#DC2626';

  return (
    <View style={styles.detailContainer}>
      <ScreenHeader
        title={salesRep.name}
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
                <Text color="muted">Email</Text>
                <Text>{salesRep.email}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Phone</Text>
                <Text>{salesRep.phone}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Territory</Text>
                <Text>{salesRep.territory}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Status</Text>
                <Badge color={salesRep.status === 'active' ? 'success' : 'secondary'}>
                  {salesRep.status}
                </Badge>
              </HStack>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Performance</Text>
              <HStack justify="between">
                <Text color="muted">Total Sales</Text>
                <Text variant="h4" weight="bold" color="success">{formatCurrency(salesRep.totalSales)}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Target</Text>
                <Text>{formatCurrency(salesRep.target)}</Text>
              </HStack>
              <HStack justify="between">
                <Text color="muted">Progress</Text>
                <Text weight="semibold" style={{ color: performanceColor }}>
                  {salesRep.performance}%
                </Text>
              </HStack>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${Math.min(progress * 100, 100)}%`, backgroundColor: performanceColor }]} />
              </View>
            </VStack>
          </Card>

          <Card>
            <VStack spacing="md">
              <Text variant="h4" weight="semibold">Clients</Text>
              <HStack justify="between">
                <Text color="muted">Active Clients</Text>
                <Text variant="h4" weight="bold">{salesRep.clients}</Text>
              </HStack>
            </VStack>
          </Card>

          <HStack spacing="sm">
            <Button variant="secondary" fullWidth>
              View Clients
            </Button>
            <Button variant="primary" fullWidth>
              Contact Rep
            </Button>
          </HStack>
        </VStack>
      </ScrollScreen>
    </View>
  );
}

export default function SalesRepsScreen() {
  const { salesReps, filteredSalesReps, searchQuery, territoryFilter, statusFilter, selectedSalesRep, isLoading, territories, setSearchQuery, setTerritoryFilter, setStatusFilter, selectSalesRep, loadSalesReps } = useSalesRepsStore();
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    loadSalesReps();
  }, [loadSalesReps]);

  const handleSalesRepPress = (salesRep: SalesRep) => {
    selectSalesRep(salesRep);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
  };

  if (showDetail && selectedSalesRep) {
    return <SalesRepDetail salesRep={selectedSalesRep} onClose={handleCloseDetail} />;
  }

  const activeReps = salesReps.filter((sr) => sr.status === 'active');
  const totalSales = salesReps.reduce((sum, sr) => sum + sr.totalSales, 0);
  const avgPerformance = salesReps.length > 0 ? salesReps.reduce((sum, sr) => sum + sr.performance, 0) / salesReps.length : 0;
  const avgPerformanceColor = avgPerformance >= 100 ? 'success' : avgPerformance >= 80 ? 'warning' : 'error';

  return (
    <ScrollScreen
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      <ScreenHeader title="Sales Team" subtitle={`${salesReps.length} total reps`} />

      <VStack spacing="md" style={styles.content}>
        <Input
          placeholder="Search reps..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          size="md"
        />

        <Section title="Territory">
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <HStack spacing="sm" style={{ paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.xs }}>
              {territories.map((territory) => (
                <Button
                  key={territory}
                  variant={territoryFilter === territory ? 'primary' : 'secondary'}
                  size="sm"
                  onPress={() => setTerritoryFilter(territory)}
                >
                  {territory}
                </Button>
              ))}
            </HStack>
          </ScrollView>
        </Section>

        <HStack spacing="sm">
          {(['all', 'active', 'inactive'] as const).map((status) => (
            <Button
              key={status}
              variant={statusFilter === status ? 'primary' : 'secondary'}
              size="sm"
              onPress={() => setStatusFilter(status)}
              style={{ flex: 1 }}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Button>
          ))}
        </HStack>

        <StatsCards style={styles.statsContainer}>
          <StatCard label="Active" value={activeReps.length} color="success" />
          <StatCard label="Total Sales" value={formatCurrency(totalSales).replace('$', '')} color="info" />
          <StatCard label="Avg Perf." value={formatPercent(avgPerformance)} color={avgPerformanceColor} />
        </StatsCards>

        <Section title={`Sales Reps (${filteredSalesReps.length})`}>
          <List variant="inset">
            {filteredSalesReps.map((salesRep) => (
              <SalesRepListItem
                key={salesRep.id}
                salesRep={salesRep}
                onPress={() => handleSalesRepPress(salesRep)}
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
  progressBar: {
    height: 8,
    backgroundColor: theme.colors.muted,
    borderRadius: 4,
    overflow: 'hidden',
    marginTop: theme.spacing.xs,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
});
